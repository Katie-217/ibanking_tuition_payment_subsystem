import datetime as dt
import secrets
import threading
import time
from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI, Header
from pydantic import BaseModel, Field

from shared import config
from shared.db import get_db
from shared.errors import (
    AppError, install_error_handlers, not_found, rate_limited,
    service_unavailable, state_conflict, validation_error,
)
from shared.security import require_uid
from shared.models.payment_models import PaymentStateWriteModel, PaymentReceiptReadModel, PaymentCreateCommandWriteModel

@asynccontextmanager
async def lifespan(_: FastAPI):
    worker = threading.Thread(target=_sweep_loop, daemon=True, name="sweep-job")
    worker.start()
    yield

app = FastAPI(title="payment-service", version="1.1", lifespan=lifespan)
install_error_handlers(app)

PAYER_URL = config.get_env("PAYER_SERVICE_URL", "http://127.0.0.1:8002")
TUITION_URL = config.get_env("TUITION_SERVICE_URL", "http://127.0.0.1:8003")
OTP_URL = config.get_env("OTP_SERVICE_URL", "http://127.0.0.1:8005")
NOTIFICATION_URL = config.get_env("NOTIFICATION_SERVICE_URL", "http://127.0.0.1:8006")

PAYMENT_TTL_SECONDS = config.get_int_env("PAYMENT_TTL_SECONDS", 300)
INTERNAL_TIMEOUT = config.get_int_env("UPSTREAM_TIMEOUT_SECONDS", 20)
RESEND_THROTTLE_SECONDS = config.get_int_env("RESEND_THROTTLE_SECONDS", 30)
SWEEP_INTERVAL_SECONDS = config.get_int_env("SWEEP_INTERVAL_SECONDS", 5)
SWEEP_BATCH = config.get_int_env("SWEEP_BATCH", 100)
COMPENSATE_RETRIES = 3

http_client = httpx.Client(timeout=INTERNAL_TIMEOUT)

PAYMENT_STATUSES = ("PENDING", "OTP_SENT", "PROCESSING", "SUCCESS",
                    "FAILED", "CANCELLED", "EXPIRED")


def _now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


def _iso(value):
    if isinstance(value, dt.datetime):
        return value.isoformat() + "Z"
    return value


def _internal_headers(payment_id: str | None = None) -> dict:
    headers = {"X-Internal-Token": config.INTERNAL_TOKEN}
    if payment_id:
        headers["X-Correlation-Id"] = str(payment_id)
    return headers


def _call(method: str, url: str, json_body: dict | None = None,
          payment_id: str | None = None) -> dict:
    try:
        resp = http_client.request(
            method, url, json=json_body,
            headers=_internal_headers(payment_id), timeout=INTERNAL_TIMEOUT,
        )
    except httpx.HTTPError:
        raise service_unavailable(f"Service nội bộ không phản hồi: {url}")

    if 200 <= resp.status_code < 300:
        return resp.json()

    try:
        err = resp.json()["error"]
        raise AppError(resp.status_code, err.get("code", "INTERNAL_ERROR"),
                       err.get("message", "Lỗi service nội bộ"), err.get("detail"))
    except (ValueError, KeyError):
        raise AppError(resp.status_code, "INTERNAL_ERROR",
                       f"Service nội bộ trả lỗi không chuẩn: {resp.text[:200]}")


def _load_payment(payment_id: str, uid: int):
    db = get_db("payment_db")
    doc = db.payments.find_one({"payment_id": payment_id})
    if not doc:
        raise not_found(f"Không tìm thấy giao dịch {payment_id}")
    if doc["uid"] != uid:
        raise AppError(403, "FORBIDDEN", "Giao dịch không thuộc về tài khoản này")
    return doc


def _transition(payment_id: str, from_statuses: tuple,
                to_status: str, reason: str | None = None,
                set_completed: bool = False) -> bool:
    db = get_db("payment_db")
    update_doc = {
        "status": to_status,
        "updated_at": _now_utc()
    }
    if reason is not None:
        update_doc["failure_reason"] = reason
    if set_completed:
        update_doc["completed_at"] = _now_utc()

    old_doc = db.payments.find_one_and_update(
        {"payment_id": payment_id, "status": {"$in": list(from_statuses)}},
        {"$set": update_doc},
        return_document=False
    )

    if old_doc:
        history_entry = {
            "payment_id": payment_id,
            "from_status": old_doc["status"],
            "to_status": to_status,
            "note": reason,
            "created_at": _now_utc()
        }
        db.payment_histories.insert_one(history_entry)
        return True

    return False


def _call_retry(method: str, url: str, json_body: dict | None = None,
                payment_id: str | None = None) -> dict:
    last: AppError | None = None
    for attempt in range(COMPENSATE_RETRIES):
        try:
            return _call(method, url, json_body, payment_id)
        except AppError as exc:
            if exc.status < 500:
                raise
            last = exc
            time.sleep(0.5 * (attempt + 1))
    raise last


def _compensate_steps(payment_id: str, uid: int, tuition_id: str, amount: float,
                      cancel_otp: bool = True) -> list[str]:
    errors: list[str] = []
    if cancel_otp:
        try:
            _call_retry("POST", f"{OTP_URL}/internal/otp/invalidate",
                        {"payment_id": payment_id}, payment_id)
        except AppError as exc:
            errors.append(f"otp/invalidate: {exc.code}")
    try:
        _call_retry("POST", f"{TUITION_URL}/internal/tuitions/{tuition_id}/release",
                    {"uid": uid, "payment_id": payment_id}, payment_id)
    except AppError as exc:
        errors.append(f"tuition/release: {exc.code}")
    try:
        _call_retry("POST", f"{PAYER_URL}/internal/balance/release",
                    {"payment_id": payment_id, "uid": uid, "amount": amount}, payment_id)
    except AppError as exc:
        errors.append(f"balance/release: {exc.code}")
    return errors


def _compensate(payment_id: str, uid: int, tuition_id: str, amount: float,
                reason: str, cancel_otp: bool = True) -> None:
    try:
        _compensate_steps(payment_id, uid, tuition_id, amount, cancel_otp)
        _transition(payment_id, ("PENDING", "OTP_SENT", "PROCESSING"), "FAILED", reason=reason)
    except Exception:
        pass


@app.get("/health")
def health():
    try:
        db = get_db("payment_db")
        db.command("ping")
        return {"status": "ok", "service": "payment-service", "database": "payment_db (MongoDB)"}
    except Exception as e:
        raise service_unavailable(f"Không kết nối được MongoDB payment_db: {str(e)}")


class CreatePaymentRequest(BaseModel):
    tuition_id: str


class VerifyOtpRequest(BaseModel):
    otp: str = Field(min_length=6, max_length=6)


@app.post("/payments", status_code=201)
def create_payment(body: CreatePaymentRequest, uid: int = Depends(require_uid),
                   idempotency_key: str = Header(default="", alias="Idempotency-Key")):
    db = get_db("payment_db")

    if idempotency_key:
        row = db.payments.find_one({"idempotency_key": idempotency_key, "uid": uid})
        if row:
            return {
                "payment_id": row["payment_id"], "status": row["status"],
                "amount": float(row["amount"]), "student_id": row["student_id"],
                "tuition_id": str(row["tuition_id"]),
                "otp_expires_in_seconds": 0, "created_at": _iso(row["created_at"]),
                "idempotent": True,
            }

    tuition = _call("GET", f"{TUITION_URL}/internal/tuitions/{body.tuition_id}?uid={uid}")
    if tuition["status"] == "PAID":
        raise AppError(409, "TUITION_ALREADY_PAID", "Khoản học phí này đã được thanh toán")
    if tuition["status"] != "UNPAID":
        raise state_conflict("Học phí đang được thanh toán bởi giao dịch khác")

    # Kiểm tra giao dịch PENDING đang có sẵn của tài khoản
    active_payment = db.payments.find_one({"uid": uid, "status": {"$in": ["PENDING", "OTP_SENT", "PROCESSING"]}})
    if active_payment:
        raise AppError(409, "PAYMENT_ALREADY_ACTIVE", "Tài khoản đã có giao dịch đang chờ xử lý")

    payment_id = f"PAY_{uid}_{secrets.token_hex(4).upper()}"
    now = _now_utc()
    expires_at = now + dt.timedelta(seconds=PAYMENT_TTL_SECONDS)

    payment_doc = {
        "payment_id": payment_id,
        "uid": uid,
        "student_id": tuition["student_id"],
        "tuition_id": str(body.tuition_id),
        "amount": float(tuition["amount"]),
        "status": "PENDING",
        "idempotency_key": idempotency_key or None,
        "expires_at": expires_at,
        "last_otp_sent_at": now,
        "created_at": now,
        "updated_at": now
    }

    db.payments.insert_one(payment_doc)

    history_entry = {
        "payment_id": payment_id,
        "from_status": None,
        "to_status": "PENDING",
        "note": "Tao giao dich",
        "created_at": now
    }
    db.payment_histories.insert_one(history_entry)

    try:
        try:
            _call("POST", f"{TUITION_URL}/internal/tuitions/{body.tuition_id}/lock",
                  {"uid": uid, "payment_id": payment_id}, payment_id)
        except AppError as exc:
            _transition(payment_id, ("PENDING",), "FAILED", reason=f"LOCK_TUITION_{exc.code}")
            raise

        payer = _call("GET", f"{PAYER_URL}/internal/payers/{uid}", payment_id=payment_id)
        try:
            otp = _call("POST", f"{OTP_URL}/internal/otp/generate",
                        {"uid": uid, "payment_id": payment_id, "email": payer["email"],
                         "purpose": "TUITION_PAYMENT"}, payment_id)
        except AppError as exc:
            _compensate(payment_id, uid, str(body.tuition_id), tuition["amount"],
                        f"OTP_GENERATE_{exc.code}", cancel_otp=False)
            raise

        try:
            _call("POST", f"{NOTIFICATION_URL}/internal/notifications/otp-email",
                  {"payment_id": payment_id, "to_email": payer["email"],
                   "to_name": payer["full_name"], "otp_code": otp["code"],
                   "expires_in": 300}, payment_id)
        except AppError as exc:
            _compensate(payment_id, uid, str(body.tuition_id), tuition["amount"],
                        f"SEND_OTP_EMAIL_{exc.code}", cancel_otp=True)
            raise service_unavailable("Không gửi được email OTP, giao dịch đã hủy — mời thử lại")

        if not _transition(payment_id, ("PENDING",), "OTP_SENT", reason=None):
            _compensate(payment_id, uid, str(body.tuition_id), tuition["amount"], "FSM_CONFLICT")
            raise state_conflict("Giao dịch vừa bị kết thúc bởi thao tác khác")
    except AppError:
        raise

    return {
        "payment_id": payment_id, "status": "OTP_SENT",
        "amount": tuition["amount"], "student_id": tuition["student_id"],
        "tuition_id": str(body.tuition_id), "otp_expires_in_seconds": 300,
        "created_at": _iso(now),
    }


@app.post("/payments/{payment_id}/verify-otp")
def verify_otp(payment_id: str, body: VerifyOtpRequest, uid: int = Depends(require_uid)):
    if not body.otp.isdigit():
        raise validation_error("Mã OTP phải gồm đúng 6 chữ số")

    row = _load_payment(payment_id, uid)
    tuition_id, amount, status = str(row["tuition_id"]), float(row["amount"]), row["status"]
    expired = row["expires_at"] < _now_utc()

    if status != "OTP_SENT":
        raise state_conflict(f"Giao dịch không ở trạng thái chờ OTP (hiện: {status})")
    if expired:
        raise state_conflict("Giao dịch đã hết hạn")

    try:
        _call("POST", f"{OTP_URL}/internal/otp/verify",
              {"payment_id": payment_id, "code": body.otp}, payment_id)
    except AppError as exc:
        if exc.code == "OTP_LOCKED":
            _compensate(payment_id, uid, tuition_id, amount, "OTP_LOCKED", cancel_otp=False)
        raise

    if not _transition(payment_id, ("OTP_SENT",), "PROCESSING"):
        raise state_conflict("Giao dịch đang được xử lý bởi request khác")

    try:
        captured = _call("POST", f"{PAYER_URL}/internal/balance/capture",
                         {"payment_id": payment_id, "uid": uid, "amount": amount},
                         payment_id)
    except AppError as exc:
        _compensate(payment_id, uid, tuition_id, amount, f"CAPTURE_{exc.code}", cancel_otp=False)
        raise

    try:
        _call("POST", f"{TUITION_URL}/internal/tuitions/{tuition_id}/paid",
              {"uid": uid, "payment_id": payment_id}, payment_id)
    except AppError as exc:
        _compensate(payment_id, uid, tuition_id, amount, f"TUITION_PAID_{exc.code}", cancel_otp=False)
        raise AppError(409, "PAYMENT_CONFLICT_CONCURRENT",
                       "Khoản học phí vừa được thanh toán bởi giao dịch khác — tiền đã được hoàn lại")

    _transition(payment_id, ("PROCESSING",), "SUCCESS", set_completed=True)
    db = get_db("payment_db")
    updated_doc = db.payments.find_one({"payment_id": payment_id})

    payer = {"full_name": ""}
    try:
        payer = _call("GET", f"{PAYER_URL}/internal/payers/{uid}", payment_id=payment_id)
        tuition = _call("GET", f"{TUITION_URL}/internal/tuitions/{tuition_id}?uid={uid}", payment_id=payment_id)
        _call("POST", f"{NOTIFICATION_URL}/internal/notifications/confirm-email",
              {"payment_id": payment_id, "to_email": payer["email"],
               "to_name": payer["full_name"], "cc_school_email": tuition["finance_email"],
               "amount": amount, "student_id": row["student_id"], "tuition_id": tuition_id,
               "completed_at": _iso(updated_doc["completed_at"])}, payment_id)
    except AppError:
        pass

    receipt = PaymentReceiptReadModel(
        payment_id=payment_id,
        uid=uid,
        student_id=row["student_id"],
        student_name=payer.get("full_name", row["student_id"]),
        tuition_id=tuition_id,
        school_name="Trường Đại học Tôn Đức Thắng",
        amount=amount,
        status="SUCCESS",
        created_at=_iso(updated_doc["created_at"]),
        updated_at=_iso(updated_doc["completed_at"])
    )

    return {
        **receipt.model_dump(),
        "balance_after": captured.get("balance_after"),
        "completed_at": _iso(updated_doc["completed_at"]),
    }


@app.post("/payments/{payment_id}/resend-otp")
def resend_otp(payment_id: str, uid: int = Depends(require_uid)):
    row = _load_payment(payment_id, uid)
    tuition_id, amount, status = str(row["tuition_id"]), float(row["amount"]), row["status"]
    expired = row["expires_at"] < _now_utc()
    last_sent = row.get("last_otp_sent_at")

    if status != "OTP_SENT":
        raise state_conflict(f"Giao dịch không ở trạng thái chờ OTP (hiện: {status})")
    if expired:
        raise state_conflict("Giao dịch đã hết hạn, không gửi lại được mã — vui lòng tạo giao dịch mới")

    if last_sent is not None:
        waited = (_now_utc() - last_sent).total_seconds()
        if waited < RESEND_THROTTLE_SECONDS:
            remaining = int(RESEND_THROTTLE_SECONDS - waited) + 1
            raise rate_limited(f"Vui lòng chờ {remaining} giây nữa mới gửi lại được")

    payer = _call("GET", f"{PAYER_URL}/internal/payers/{uid}", payment_id=payment_id)
    otp = _call("POST", f"{OTP_URL}/internal/otp/generate",
                {"uid": uid, "payment_id": payment_id, "email": payer["email"],
                 "purpose": "TUITION_PAYMENT"}, payment_id)

    db = get_db("payment_db")
    db.payments.update_one({"payment_id": payment_id}, {"$set": {"last_otp_sent_at": _now_utc()}})

    try:
        _call("POST", f"{NOTIFICATION_URL}/internal/notifications/otp-email",
              {"payment_id": payment_id, "to_email": payer["email"],
               "to_name": payer["full_name"], "otp_code": otp["code"],
               "expires_in": 300}, payment_id)
    except AppError:
        raise service_unavailable("Không gửi được email — mã mới đã sinh, vui lòng thử gửi lại sau ít giây")

    return {"payment_id": payment_id, "otp_expires_in_seconds": 300}


@app.post("/payments/{payment_id}/cancel")
def cancel_payment(payment_id: str, uid: int = Depends(require_uid)):
    row = _load_payment(payment_id, uid)
    tuition_id, amount, status = str(row["tuition_id"]), float(row["amount"]), row["status"]

    if status not in ("PENDING", "OTP_SENT"):
        raise state_conflict(f"Không thể hủy giao dịch ở trạng thái {status}")

    if not _transition(payment_id, ("PENDING", "OTP_SENT"), "CANCELLED", reason="NGUOI_DUNG_HUY"):
        raise state_conflict("Giao dịch đang được xử lý bởi request khác")

    errors = _compensate_steps(payment_id, uid, tuition_id, amount)
    if errors:
        raise service_unavailable("Giao dịch đã hủy nhưng chưa dọn hết hệ quả: " + "; ".join(errors))
    return {"payment_id": payment_id, "status": "CANCELLED"}


@app.get("/payments")
def list_payments(status: str = "", page: int = 1, size: int = 20,
                  uid: int = Depends(require_uid)):
    if status and status not in PAYMENT_STATUSES:
        raise validation_error(f"status không hợp lệ (chấp nhận: {', '.join(PAYMENT_STATUSES)})")
    if page < 1 or size < 1 or size > 100:
        raise validation_error("page >= 1 và 1 <= size <= 100")

    db = get_db("payment_db")
    query = {"uid": uid}
    if status:
        query["status"] = status

    total = db.payments.count_documents(query)
    skip = (page - 1) * size
    cursor = db.payments.find(query).sort("created_at", -1).skip(skip).limit(size)

    items = []
    for r in cursor:
        items.append({
            "payment_id": r["payment_id"],
            "status": r["status"],
            "amount": float(r["amount"]),
            "student_id": r["student_id"],
            "tuition_id": str(r["tuition_id"]),
            "created_at": _iso(r["created_at"]),
            "completed_at": _iso(r.get("completed_at")),
            "failure_reason": r.get("failure_reason"),
        })

    return {
        "items": items,
        "page": page,
        "size": size,
        "total": total,
    }


@app.get("/payments/{payment_id}")
def get_payment(payment_id: str, uid: int = Depends(require_uid)):
    row = _load_payment(payment_id, uid)
    db = get_db("payment_db")

    history_cursor = db.payment_histories.find({"payment_id": payment_id}).sort("created_at", 1)
    history = list(history_cursor)

    return {
        "payment_id": row["payment_id"],
        "status": row["status"],
        "amount": float(row["amount"]),
        "student_id": row["student_id"],
        "tuition_id": str(row["tuition_id"]),
        "created_at": _iso(row["created_at"]),
        "completed_at": _iso(row.get("completed_at")),
        "expires_at": _iso(row.get("expires_at")),
        "failure_reason": row.get("failure_reason"),
        "history": [
            {
                "from_status": h.get("from_status"),
                "to_status": h.get("to_status"),
                "note": h.get("note"),
                "at": _iso(h.get("created_at"))
            }
            for h in history
        ],
    }


def _sweep_once() -> None:
    try:
        result = _call("POST", f"{OTP_URL}/internal/otp/sweep-expired")
        if result.get("expired"):
            print(f"[sweep] {result['expired']} OTP -> EXPIRED")
    except AppError as exc:
        print(f"[sweep] otp/sweep-expired error: {exc.code} - retry next cycle")

    db = get_db("payment_db")
    expired_payments = db.payments.find({
        "status": {"$in": ["PENDING", "OTP_SENT", "PROCESSING"]},
        "expires_at": {"$lte": _now_utc()}
    }).limit(SWEEP_BATCH)

    for row in expired_payments:
        _expire_payment(row["payment_id"], row["uid"], str(row["tuition_id"]), float(row["amount"]))


def _expire_payment(payment_id: str, uid: int, tuition_id: str, amount: float) -> None:
    try:
        tuition = _call("GET", f"{TUITION_URL}/internal/tuitions/{tuition_id}?uid={uid}", payment_id=payment_id)
        if tuition.get("status") == "PAID":
            _transition(payment_id, ("PENDING", "OTP_SENT", "PROCESSING"), "SUCCESS", set_completed=True)
            print(f"[sweep] payment {payment_id}: tuition already PAID -> finalize SUCCESS")
            return
    except AppError as exc:
        print(f"[sweep] payment {payment_id}: read tuition error {exc.code} - retry next cycle")
        return

    errors = _compensate_steps(payment_id, uid, tuition_id, amount)
    if errors:
        print(f"[sweep] payment {payment_id}: compensation pending {errors} - retry next cycle")
        return

    if _transition(payment_id, ("PENDING", "OTP_SENT", "PROCESSING"), "EXPIRED", reason="Hết hạn — job quét hủy"):
        print(f"[sweep] payment {payment_id} -> EXPIRED (tuition {tuition_id} unlocked)")


def _sweep_loop() -> None:
    print(f"[sweep] sweeper started (interval {SWEEP_INTERVAL_SECONDS}s)")
    while True:
        try:
            _sweep_once()
        except Exception as exc:
            print(f"[sweep] cycle error: {exc!r}")
        time.sleep(SWEEP_INTERVAL_SECONDS)

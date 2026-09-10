import datetime as dt
import threading
import time
from contextlib import asynccontextmanager

import httpx
import pyodbc
from fastapi import Depends, FastAPI, Header
from pydantic import BaseModel, Field

from shared import config
from shared.db import connect, is_unique_violation
from shared.errors import (
    AppError, install_error_handlers, not_found, rate_limited,
    service_unavailable, state_conflict, validation_error,
)
from shared.security import require_uid

@asynccontextmanager
async def lifespan(_: FastAPI):
    worker = threading.Thread(target=_sweep_loop, daemon=True, name="sweep-job")
    worker.start()
    yield

app = FastAPI(title="payment-service", version="1.1", lifespan=lifespan)
install_error_handlers(app)

PAYER_URL = config.get_env("PAYER_SERVICE_URL", "http://localhost:8002")
TUITION_URL = config.get_env("TUITION_SERVICE_URL", "http://localhost:8003")
OTP_URL = config.get_env("OTP_SERVICE_URL", "http://localhost:8005")
NOTIFICATION_URL = config.get_env("NOTIFICATION_SERVICE_URL", "http://localhost:8006")

PAYMENT_TTL_SECONDS = config.get_int_env("PAYMENT_TTL_SECONDS", 300)
INTERNAL_TIMEOUT = config.get_int_env("UPSTREAM_TIMEOUT_SECONDS", 20)
RESEND_THROTTLE_SECONDS = config.get_int_env("RESEND_THROTTLE_SECONDS", 30)
SWEEP_INTERVAL_SECONDS = config.get_int_env("SWEEP_INTERVAL_SECONDS", 5)
SWEEP_BATCH = config.get_int_env("SWEEP_BATCH", 100)
COMPENSATE_RETRIES = 3

PAYMENT_STATUSES = ("PENDING", "OTP_SENT", "PROCESSING", "SUCCESS",
                    "FAILED", "CANCELLED", "EXPIRED")


def _now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


def _iso(value):
    return value.isoformat() + "Z" if isinstance(value, dt.datetime) else value


def _internal_headers(payment_id: int | None = None) -> dict:
    headers = {"X-Internal-Token": config.INTERNAL_TOKEN}
    if payment_id:
        headers["X-Correlation-Id"] = str(payment_id)
    return headers


def _call(method: str, url: str, json_body: dict | None = None,
          payment_id: int | None = None) -> dict:
    try:
        resp = httpx.request(
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


def _load_payment(c: pyodbc.Connection, payment_id: int, uid: int):
    row = c.execute(
        "SELECT payment_id, uid, student_id, tuition_id, amount, status, failure_reason, "
        "created_at, expires_at, completed_at, last_otp_sent_at "
        "FROM dbo.payments WHERE payment_id = ?",
        payment_id,
    ).fetchone()
    if row is None:
        raise not_found(f"Không tìm thấy giao dịch {payment_id}")
    if row.uid != uid:
        raise AppError(403, "FORBIDDEN", "Giao dịch không thuộc về tài khoản này")
    return row


def _transition(c: pyodbc.Connection, payment_id: int, from_statuses: tuple,
                to_status: str, reason: str | None = None,
                set_completed: bool = False) -> bool:
    sql = "UPDATE dbo.payments SET status = ?"
    params: list = [to_status]
    if reason is not None:
        sql += ", failure_reason = ?"
        params.append(reason)
    if set_completed:
        sql += ", completed_at = SYSUTCDATETIME()"

    sql += (" OUTPUT deleted.status"
            f" WHERE payment_id = ? AND status IN ({','.join('?' * len(from_statuses))})")
    params += [payment_id, *from_statuses]
    cur = c.execute(sql, *params)
    old = cur.fetchone()
    if old is not None:
        c.execute(
            "INSERT INTO dbo.payment_history (payment_id, from_status, to_status, note) "
            "VALUES (?, ?, ?, ?)",
            payment_id, old.status, to_status, reason,
        )
    return old is not None


def _compensate_steps(payment_id: int, uid: int, tuition_id: int, amount: int,
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


def _call_retry(method: str, url: str, json_body: dict | None = None,
                payment_id: int | None = None) -> dict:
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


def _compensate(payment_id: int, uid: int, tuition_id: int, amount: int,
                reason: str, cancel_otp: bool = True) -> None:
    try:
        _compensate_steps(payment_id, uid, tuition_id, amount, cancel_otp)
        with connect("PaymentDB") as c:
            _transition(c, payment_id, ("PENDING", "OTP_SENT", "PROCESSING"),
                        "FAILED", reason=reason)
    except Exception:
        pass


@app.get("/health")
def health():
    try:
        with connect("PaymentDB") as c:
            c.execute("SELECT 1").fetchone()
        return {"status": "ok", "service": "payment-service"}
    except pyodbc.Error:
        raise service_unavailable("Không kết nối được database PaymentDB")


class CreatePaymentRequest(BaseModel):
    tuition_id: int = Field(gt=0)


class VerifyOtpRequest(BaseModel):
    otp: str = Field(min_length=6, max_length=6)


@app.post("/payments", status_code=201)
def create_payment(body: CreatePaymentRequest, uid: int = Depends(require_uid),
                   idempotency_key: str = Header(default="", alias="Idempotency-Key")):
    if idempotency_key:
        with connect("PaymentDB") as c:
            row = c.execute(
                "SELECT payment_id, status, amount, student_id, tuition_id, created_at "
                "FROM dbo.payments WHERE idempotency_key = ? AND uid = ?",
                idempotency_key, uid,
            ).fetchone()
        if row is not None:
            return {
                "payment_id": int(row.payment_id), "status": row.status,
                "amount": int(row.amount), "student_id": row.student_id,
                "tuition_id": int(row.tuition_id),
                "otp_expires_in_seconds": 0, "created_at": _iso(row.created_at),
                "idempotent": True,
            }

    tuition = _call("GET", f"{TUITION_URL}/internal/tuitions/{body.tuition_id}?uid={uid}")
    if tuition["status"] == "PAID":
        raise AppError(409, "TUITION_ALREADY_PAID", "Khoản học phí này đã được thanh toán")
    if tuition["status"] != "UNPAID":
        raise state_conflict("Học phí đang được thanh toán bởi giao dịch khác")

    try:
        with connect("PaymentDB") as c:
            cur = c.execute(
                "INSERT INTO dbo.payments (uid, student_id, tuition_id, amount, idempotency_key, "
                "expires_at, last_otp_sent_at) OUTPUT INSERTED.payment_id, INSERTED.created_at "
                "VALUES (?, ?, ?, ?, ?, DATEADD(SECOND, ?, SYSUTCDATETIME()), SYSUTCDATETIME())",
                uid, tuition["student_id"], body.tuition_id, tuition["amount"],
                idempotency_key or None, PAYMENT_TTL_SECONDS,
            )
            new = cur.fetchone()
            payment_id, created_at = int(new.payment_id), new.created_at
            c.execute(
                "INSERT INTO dbo.payment_history (payment_id, from_status, to_status, note) "
                "VALUES (?, NULL, N'PENDING', N'Tao giao dich')", payment_id,
            )
    except pyodbc.IntegrityError as exc:
        if not is_unique_violation(exc):
            raise

        with connect("PaymentDB") as c:
            row = c.execute(
                "SELECT payment_id, status, amount, student_id, tuition_id, created_at "
                "FROM dbo.payments WHERE idempotency_key = ? AND uid = ?",
                idempotency_key, uid,
            ).fetchone()
        if row is not None and idempotency_key:
            return {
                "payment_id": int(row.payment_id), "status": row.status,
                "amount": int(row.amount), "student_id": row.student_id,
                "tuition_id": int(row.tuition_id),
                "otp_expires_in_seconds": 0, "created_at": _iso(row.created_at),
                "idempotent": True,
            }
        raise AppError(409, "PAYMENT_ALREADY_ACTIVE",
                       "Tài khoản đã có giao dịch đang chờ xử lý (BR-07)")
    try:
        try:
            _call("POST", f"{TUITION_URL}/internal/tuitions/{body.tuition_id}/lock",
                  {"uid": uid, "payment_id": payment_id}, payment_id)
        except AppError as exc:
            with connect("PaymentDB") as c:
                _transition(c, payment_id, ("PENDING",), "FAILED",
                            reason=f"LOCK_TUITION_{exc.code}")
            raise

        payer = _call("GET", f"{PAYER_URL}/internal/payers/{uid}", payment_id=payment_id)
        try:
            otp = _call("POST", f"{OTP_URL}/internal/otp/generate",
                        {"uid": uid, "payment_id": payment_id, "email": payer["email"],
                         "purpose": "TUITION_PAYMENT"}, payment_id)
        except AppError as exc:
            _compensate(payment_id, uid, body.tuition_id, tuition["amount"],
                        f"OTP_GENERATE_{exc.code}", cancel_otp=False)
            raise

        try:
            _call("POST", f"{NOTIFICATION_URL}/internal/notifications/otp-email",
                  {"payment_id": payment_id, "to_email": payer["email"],
                   "to_name": payer["full_name"], "otp_code": otp["code"],
                   "expires_in": 300}, payment_id)
        except AppError as exc:
            _compensate(payment_id, uid, body.tuition_id, tuition["amount"],
                        f"SEND_OTP_EMAIL_{exc.code}", cancel_otp=True)
            raise service_unavailable("Không gửi được email OTP, giao dịch đã hủy — mời thử lại")

        with connect("PaymentDB") as c:
            if not _transition(c, payment_id, ("PENDING",), "OTP_SENT",
                               reason=None):
                _compensate(payment_id, uid, body.tuition_id, tuition["amount"],
                            "FSM_CONFLICT")
                raise state_conflict("Giao dịch vừa bị kết thúc bởi thao tác khác")
    except AppError:
        raise

    return {
        "payment_id": payment_id, "status": "OTP_SENT",
        "amount": tuition["amount"], "student_id": tuition["student_id"],
        "tuition_id": body.tuition_id, "otp_expires_in_seconds": 300,
        "created_at": _iso(created_at),
    }


@app.post("/payments/{payment_id}/verify-otp")
def verify_otp(payment_id: int, body: VerifyOtpRequest, uid: int = Depends(require_uid)):
    if not body.otp.isdigit():
        raise validation_error("Mã OTP phải gồm đúng 6 chữ số")

    with connect("PaymentDB") as c:
        row = _load_payment(c, payment_id, uid)
        tuition_id, amount, status = int(row.tuition_id), int(row.amount), row.status
        expired = row.expires_at < _now_utc()
    if status != "OTP_SENT":
        raise state_conflict(f"Giao dịch không ở trạng thái chờ OTP (hiện: {status})")
    if expired:
        raise state_conflict("Giao dịch đã hết hạn")

    try:
        _call("POST", f"{OTP_URL}/internal/otp/verify",
              {"payment_id": payment_id, "code": body.otp}, payment_id)
    except AppError as exc:
        if exc.code == "OTP_LOCKED":
            _compensate(payment_id, uid, tuition_id, amount, "OTP_LOCKED",
                        cancel_otp=False)
        raise

    with connect("PaymentDB") as c:
        if not _transition(c, payment_id, ("OTP_SENT",), "PROCESSING"):
            raise state_conflict("Giao dịch đang được xử lý bởi request khác")

    try:
        captured = _call("POST", f"{PAYER_URL}/internal/balance/capture",
                         {"payment_id": payment_id, "uid": uid, "amount": amount},
                         payment_id)
    except AppError as exc:
        _compensate(payment_id, uid, tuition_id, amount, f"CAPTURE_{exc.code}",
                    cancel_otp=False)
        raise

    try:
        _call("POST", f"{TUITION_URL}/internal/tuitions/{tuition_id}/paid",
              {"uid": uid, "payment_id": payment_id}, payment_id)
    except AppError as exc:
        _compensate(payment_id, uid, tuition_id, amount, f"TUITION_PAID_{exc.code}",
                    cancel_otp=False)
        raise AppError(409, "PAYMENT_CONFLICT_CONCURRENT",
                       "Khoản học phí vừa được thanh toán bởi giao dịch khác — tiền đã được hoàn lại")

    with connect("PaymentDB") as c:
        _transition(c, payment_id, ("PROCESSING",), "SUCCESS", set_completed=True)
        completed = c.execute(
            "SELECT completed_at FROM dbo.payments WHERE payment_id = ?", payment_id,
        ).fetchone()

    payer = {"full_name": ""}
    try:
        payer = _call("GET", f"{PAYER_URL}/internal/payers/{uid}", payment_id=payment_id)
        tuition = _call("GET", f"{TUITION_URL}/internal/tuitions/{tuition_id}?uid={uid}",
                        payment_id=payment_id)
        _call("POST", f"{NOTIFICATION_URL}/internal/notifications/confirm-email",
              {"payment_id": payment_id, "to_email": payer["email"],
               "to_name": payer["full_name"], "cc_school_email": tuition["finance_email"],
               "amount": amount, "student_id": row.student_id, "tuition_id": tuition_id,
               "completed_at": _iso(completed.completed_at)}, payment_id)
    except AppError:
        pass

    return {
        "payment_id": payment_id, "status": "SUCCESS", "amount": amount,
        "student": {"student_id": row.student_id,
                    "full_name": payer.get("full_name", "")},
        "tuition_id": tuition_id, "balance_after": captured.get("balance_after"),
        "completed_at": _iso(completed.completed_at),
    }


@app.post("/payments/{payment_id}/resend-otp")
def resend_otp(payment_id: int, uid: int = Depends(require_uid)):
    with connect("PaymentDB") as c:
        row = _load_payment(c, payment_id, uid)
        tuition_id, amount, status = int(row.tuition_id), int(row.amount), row.status
        expired = row.expires_at < _now_utc()
        last_sent = row.last_otp_sent_at
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

    with connect("PaymentDB") as c:
        c.execute("UPDATE dbo.payments SET last_otp_sent_at = SYSUTCDATETIME() "
                  "WHERE payment_id = ?", payment_id)

    try:
        _call("POST", f"{NOTIFICATION_URL}/internal/notifications/otp-email",
              {"payment_id": payment_id, "to_email": payer["email"],
               "to_name": payer["full_name"], "otp_code": otp["code"],
               "expires_in": 300}, payment_id)
    except AppError:
        raise service_unavailable(
            "Không gửi được email — mã mới đã sinh, vui lòng thử gửi lại sau ít giây")

    return {"payment_id": payment_id, "otp_expires_in_seconds": 300}


@app.post("/payments/{payment_id}/cancel")
def cancel_payment(payment_id: int, uid: int = Depends(require_uid)):
    with connect("PaymentDB") as c:
        row = _load_payment(c, payment_id, uid)
        tuition_id, amount, status = int(row.tuition_id), int(row.amount), row.status
    if status not in ("PENDING", "OTP_SENT"):
        raise state_conflict(f"Không thể hủy giao dịch ở trạng thái {status}")

    with connect("PaymentDB") as c:
        if not _transition(c, payment_id, ("PENDING", "OTP_SENT"), "CANCELLED",
                           reason="NGUOI_DUNG_HUY"):
            raise state_conflict("Giao dịch đang được xử lý bởi request khác")

    errors = _compensate_steps(payment_id, uid, tuition_id, amount)
    if errors:
        raise service_unavailable(
            "Giao dịch đã hủy nhưng chưa dọn hết hệ quả: " + "; ".join(errors))
    return {"payment_id": payment_id, "status": "CANCELLED"}


@app.get("/payments")
def list_payments(status: str = "", page: int = 1, size: int = 20,
                  uid: int = Depends(require_uid)):
    if status and status not in PAYMENT_STATUSES:
        raise validation_error(
            f"status không hợp lệ (chấp nhận: {', '.join(PAYMENT_STATUSES)})")
    if page < 1 or size < 1 or size > 100:
        raise validation_error("page >= 1 và 1 <= size <= 100")

    where = "uid = ?"
    params: list = [uid]
    if status:
        where += " AND status = ?"
        params.append(status)

    with connect("PaymentDB") as c:
        total = c.execute(f"SELECT COUNT(*) FROM dbo.payments WHERE {where}", *params).fetchone()[0]
        rows = c.execute(
            f"SELECT payment_id, student_id, tuition_id, amount, status, failure_reason, "
            f"created_at, completed_at FROM dbo.payments WHERE {where} "
            f"ORDER BY created_at DESC, payment_id DESC OFFSET ? ROWS FETCH NEXT ? ROWS ONLY",
            *params, (page - 1) * size, size,
        ).fetchall()

    return {
        "items": [
            {
                "payment_id": int(r.payment_id), "status": r.status,
                "amount": int(r.amount), "student_id": r.student_id,
                "tuition_id": int(r.tuition_id), "created_at": _iso(r.created_at),
                "completed_at": _iso(r.completed_at), "failure_reason": r.failure_reason,
            }
            for r in rows
        ],
        "page": page, "size": size, "total": int(total),
    }


@app.get("/payments/{payment_id}")
def get_payment(payment_id: int, uid: int = Depends(require_uid)):
    with connect("PaymentDB") as c:
        row = _load_payment(c, payment_id, uid)
        history = c.execute(
            "SELECT from_status, to_status, note, created_at FROM dbo.payment_history "
            "WHERE payment_id = ? ORDER BY history_id",
            payment_id,
        ).fetchall()
    return {
        "payment_id": int(row.payment_id), "status": row.status,
        "amount": int(row.amount), "student_id": row.student_id,
        "tuition_id": int(row.tuition_id),
        "created_at": _iso(row.created_at), "completed_at": _iso(row.completed_at),
        "expires_at": _iso(row.expires_at), "failure_reason": row.failure_reason,
        "history": [
            {"from_status": h.from_status, "to_status": h.to_status,
             "note": h.note, "at": _iso(h.created_at)}
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

    with connect("PaymentDB") as c:
        rows = c.execute(
            "SELECT TOP (?) payment_id, uid, tuition_id, amount, status FROM dbo.payments "
            "WHERE status IN (N'PENDING', N'OTP_SENT', N'PROCESSING') "
            "AND expires_at <= SYSUTCDATETIME() ORDER BY payment_id",
            SWEEP_BATCH,
        ).fetchall()

    for row in rows:
        _expire_payment(int(row.payment_id), row.uid, int(row.tuition_id),
                        int(row.amount))


def _expire_payment(payment_id: int, uid: int, tuition_id: int, amount: int) -> None:
    try:
        tuition = _call("GET", f"{TUITION_URL}/internal/tuitions/{tuition_id}?uid={uid}",
                        payment_id=payment_id)
        if tuition.get("status") == "PAID":
            with connect("PaymentDB") as c:
                _transition(c, payment_id, ("PENDING", "OTP_SENT", "PROCESSING"),
                            "SUCCESS", set_completed=True)
            print(f"[sweep] payment {payment_id}: tuition already PAID -> finalize SUCCESS")
            return
    except AppError as exc:
        print(f"[sweep] payment {payment_id}: read tuition error {exc.code} - retry next cycle")
        return

    errors = _compensate_steps(payment_id, uid, tuition_id, amount)
    if errors:
        print(f"[sweep] payment {payment_id}: compensation pending {errors} - retry next cycle")
        return
    with connect("PaymentDB") as c:
        if _transition(c, payment_id, ("PENDING", "OTP_SENT", "PROCESSING"),
                       "EXPIRED", reason="Hết hạn — job quét hủy"):
            print(f"[sweep] payment {payment_id} -> EXPIRED (tuition {tuition_id} unlocked)")


def _sweep_loop() -> None:
    print(f"[sweep] sweeper started (interval {SWEEP_INTERVAL_SECONDS}s)")
    while True:
        try:
            _sweep_once()
        except Exception as exc:
            print(f"[sweep] cycle error: {exc!r}")
        time.sleep(SWEEP_INTERVAL_SECONDS)

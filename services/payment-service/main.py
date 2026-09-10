"""payment-service (:8004) — ORCHESTRATOR thanh toán học phí.

Vai trò: điều phối toàn bộ luồng thanh toán giữa payer / tuition / otp / notification
service, quản lý FSM trạng thái giao dịch và saga bù trừ (docs/05, docs/06).

FSM trạng thái payment (BR-12, không cho chuyển tùy ý):
    PENDING → OTP_SENT → PROCESSING → SUCCESS
    PENDING/OTP_SENT → CANCELLED (FR-06, user hủy)
    PENDING/OTP_SENT → EXPIRED    (FR-08, job quét)
    OTP_SENT/PROCESSING → FAILED  (OTP_LOCKED, thiếu dư, xung đột concurrent…)

Saga bù trừ — mỗi bước gọi service con có "cặp bù" idempotent:
    lock tuition   ↔ release tuition
    capture balance ↔ release balance (chỉ hoàn khi ledger có CAPTURE)
Bước nào fail → gọi bù cho các bước ĐÃ thành công rồi mới trả lỗi cho user.

Port mặc định: 8004. Chạy:
    python -m uvicorn main:app --port 8004 --app-dir services/payment-service --reload
"""
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
    """FR-08 — khởi động job quét hết hạn chạy nền (daemon thread) cùng app."""
    worker = threading.Thread(target=_sweep_loop, daemon=True, name="sweep-job")
    worker.start()
    yield


app = FastAPI(title="payment-service", version="1.1", lifespan=lifespan)
install_error_handlers(app)

PAYER_URL = config.get_env("PAYER_SERVICE_URL", "http://localhost:8002")
TUITION_URL = config.get_env("TUITION_SERVICE_URL", "http://localhost:8003")
OTP_URL = config.get_env("OTP_SERVICE_URL", "http://localhost:8005")
NOTIFICATION_URL = config.get_env("NOTIFICATION_SERVICE_URL", "http://localhost:8006")

PAYMENT_TTL_SECONDS = config.get_int_env("PAYMENT_TTL_SECONDS", 300)  # gd sống tối đa 5 phút
INTERNAL_TIMEOUT = config.get_int_env("UPSTREAM_TIMEOUT_SECONDS", 20)
RESEND_THROTTLE_SECONDS = config.get_int_env("RESEND_THROTTLE_SECONDS", 30)  # FR-05
SWEEP_INTERVAL_SECONDS = config.get_int_env("SWEEP_INTERVAL_SECONDS", 5)     # FR-08: 5–10s
SWEEP_BATCH = config.get_int_env("SWEEP_BATCH", 100)                         # FR-08: quét theo đợt
COMPENSATE_RETRIES = 3

PAYMENT_STATUSES = ("PENDING", "OTP_SENT", "PROCESSING", "SUCCESS",
                    "FAILED", "CANCELLED", "EXPIRED")


def _now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


def _iso(value):
    return value.isoformat() + "Z" if isinstance(value, dt.datetime) else value


# ------------------------- Gọi service con (REST nội bộ) -------------------------
def _internal_headers(payment_id: int | None = None) -> dict:
    headers = {"X-Internal-Token": config.INTERNAL_TOKEN}
    if payment_id:
        headers["X-Correlation-Id"] = str(payment_id)
    return headers


def _call(method: str, url: str, json_body: dict | None = None,
          payment_id: int | None = None) -> dict:
    """Gọi 1 endpoint nội bộ. Lỗi nghiệp vụ của service con được propagate NGUYÊN VẸN
    (đúng status + code + message); service chết → 503 SERVICE_UNAVAILABLE."""
    try:
        resp = httpx.request(
            method, url, json=json_body,
            headers=_internal_headers(payment_id), timeout=INTERNAL_TIMEOUT,
        )
    except httpx.HTTPError:
        raise service_unavailable(f"Service nội bộ không phản hồi: {url}")

    if 200 <= resp.status_code < 300:
        return resp.json()
    # chuyển tiếp envelope lỗi của service con
    try:
        err = resp.json()["error"]
        raise AppError(resp.status_code, err.get("code", "INTERNAL_ERROR"),
                       err.get("message", "Lỗi service nội bộ"), err.get("detail"))
    except (ValueError, KeyError):
        raise AppError(resp.status_code, "INTERNAL_ERROR",
                       f"Service nội bộ trả lỗi không chuẩn: {resp.text[:200]}")


# ------------------------- Helper PaymentDB -------------------------
def _load_payment(c: pyodbc.Connection, payment_id: int, uid: int):
    """Lấy payment + kiểm tra chủ sở hữu (403 nếu không phải của uid)."""
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
    """Chuyển trạng thái FSM có điều kiện — chỉ thành công khi status hiện tại nằm trong
    from_statuses (conditional UPDATE chống 2 request song song). Trả False nếu thua."""
    sql = "UPDATE dbo.payments SET status = ?"
    params: list = [to_status]
    if reason is not None:
        sql += ", failure_reason = ?"
        params.append(reason)
    if set_completed:
        sql += ", completed_at = SYSUTCDATETIME()"
    # OUTPUT deleted.status = trạng thái CŨ trước khi UPDATE
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
    """Dọn hệ quả của giao dịch: vô hiệu OTP + mở khóa tuition + hoàn tiền nếu đã capture.

    Mọi bước idempotent, mỗi bước thử lại COMPENSATE_RETRIES lần (service con chết
    tạm thời). Trả danh sách lỗi còn vướng — rỗng là sạch (FR-06/FR-08 gọi lại được).
    """
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
    """_call + thử lại khi service con chết tạm thời (503/timeout). Lỗi nghiệp vụ
    (4xx từ service con) KHÔNG retry — retry cũng ra cùng lỗi."""
    last: AppError | None = None
    for attempt in range(COMPENSATE_RETRIES):
        try:
            return _call(method, url, json_body, payment_id)
        except AppError as exc:
            if exc.status < 500:
                raise   # lỗi nghiệp vụ — retry cũng ra cùng lỗi
            last = exc
            time.sleep(0.5 * (attempt + 1))
    raise last


def _compensate(payment_id: int, uid: int, tuition_id: int, amount: int,
                reason: str, cancel_otp: bool = True) -> None:
    """Saga bù trừ khi giao dịch thất bại giữa chừng (FR-03/FR-04): dọn hệ quả
    rồi chuyển payment sang FAILED. Bọc try/except để không che lỗi gốc."""
    try:
        _compensate_steps(payment_id, uid, tuition_id, amount, cancel_otp)
        with connect("PaymentDB") as c:
            _transition(c, payment_id, ("PENDING", "OTP_SENT", "PROCESSING"),
                        "FAILED", reason=reason)
    except Exception:  # noqa: BLE001 — bù trừ lỗi không được che mất lỗi gốc
        pass


# ------------------------- API -------------------------
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
    """FR-03 — Tạo giao dịch + khóa học phí + sinh OTP + gửi email. CHƯA trừ tiền (BR-06)."""
    # (a) Idempotency-Key: retry trả lại payment đã tạo, không tạo mới
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

    # (b) Đọc tuition: tồn tại + thuộc uid (BR-04) + trạng thái
    tuition = _call("GET", f"{TUITION_URL}/internal/tuitions/{body.tuition_id}?uid={uid}")
    if tuition["status"] == "PAID":
        raise AppError(409, "TUITION_ALREADY_PAID", "Khoản học phí này đã được thanh toán")
    if tuition["status"] != "UNPAID":
        raise state_conflict("Học phí đang được thanh toán bởi giao dịch khác")

    # (c) Tạo payment PENDING — unique index chặn 2 gd active cùng uid (BR-07)
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
        # 2 request song song: 1 thắng, 1 thua ở unique index → trả về đúng lỗi
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
        # (d) Khóa tuition UNPAID→PAYING (Case B — chống 2 tài khoản cùng thanh toán)
        try:
            _call("POST", f"{TUITION_URL}/internal/tuitions/{body.tuition_id}/lock",
                  {"uid": uid, "payment_id": payment_id}, payment_id)
        except AppError as exc:
            with connect("PaymentDB") as c:
                _transition(c, payment_id, ("PENDING",), "FAILED",
                            reason=f"LOCK_TUITION_{exc.code}")
            raise

        # (e) Sinh OTP (otp-service tự chuyển OTP ACTIVE cũ sang REPLACED)
        payer = _call("GET", f"{PAYER_URL}/internal/payers/{uid}", payment_id=payment_id)
        try:
            otp = _call("POST", f"{OTP_URL}/internal/otp/generate",
                        {"uid": uid, "payment_id": payment_id, "email": payer["email"],
                         "purpose": "TUITION_PAYMENT"}, payment_id)
        except AppError as exc:
            _compensate(payment_id, uid, body.tuition_id, tuition["amount"],
                        f"OTP_GENERATE_{exc.code}", cancel_otp=False)
            raise

        # (f) Gửi email chứa OTP — lỗi → bù trừ toàn bộ (FR-03)
        try:
            _call("POST", f"{NOTIFICATION_URL}/internal/notifications/otp-email",
                  {"payment_id": payment_id, "to_email": payer["email"],
                   "to_name": payer["full_name"], "otp_code": otp["code"],
                   "expires_in": 300}, payment_id)
        except AppError as exc:
            _compensate(payment_id, uid, body.tuition_id, tuition["amount"],
                        f"SEND_OTP_EMAIL_{exc.code}", cancel_otp=True)
            raise service_unavailable("Không gửi được email OTP, giao dịch đã hủy — mời thử lại")

        # (g) PENDING → OTP_SENT (FSM)
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
    """FR-04 — Xác thực OTP rồi mới capture tiền → PAID → SUCCESS → email xác nhận."""
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

    # (b) Xác thực OTP ở otp-service — lỗi mã propagated nguyên vẹn
    try:
        _call("POST", f"{OTP_URL}/internal/otp/verify",
              {"payment_id": payment_id, "code": body.otp}, payment_id)
    except AppError as exc:
        if exc.code == "OTP_LOCKED":
            # Sai đủ 5 lần → hủy giao dịch + mở khóa học phí, KHÔNG hoàn tiền (chưa capture)
            _compensate(payment_id, uid, tuition_id, amount, "OTP_LOCKED",
                        cancel_otp=False)
        raise

    # (c) OTP_SENT → PROCESSING (conditional UPDATE chống verify song song)
    with connect("PaymentDB") as c:
        if not _transition(c, payment_id, ("OTP_SENT",), "PROCESSING"):
            raise state_conflict("Giao dịch đang được xử lý bởi request khác")

    # (d) Capture tiền — thiếu dư → FAILED + mở khóa học phí, không hoàn (chưa trừ)
    try:
        captured = _call("POST", f"{PAYER_URL}/internal/balance/capture",
                         {"payment_id": payment_id, "uid": uid, "amount": amount},
                         payment_id)
    except AppError as exc:
        _compensate(payment_id, uid, tuition_id, amount, f"CAPTURE_{exc.code}",
                    cancel_otp=False)
        raise

    # (e) Tuition PAYING→PAID — thua (concurrent) → hoàn tiền + FAILED
    try:
        _call("POST", f"{TUITION_URL}/internal/tuitions/{tuition_id}/paid",
              {"uid": uid, "payment_id": payment_id}, payment_id)
    except AppError as exc:
        _compensate(payment_id, uid, tuition_id, amount, f"TUITION_PAID_{exc.code}",
                    cancel_otp=False)
        raise AppError(409, "PAYMENT_CONFLICT_CONCURRENT",
                       "Khoản học phí vừa được thanh toán bởi giao dịch khác — tiền đã được hoàn lại")

    # (f) PROCESSING → SUCCESS + completed_at
    with connect("PaymentDB") as c:
        _transition(c, payment_id, ("PROCESSING",), "SUCCESS", set_completed=True)
        completed = c.execute(
            "SELECT completed_at FROM dbo.payments WHERE payment_id = ?", payment_id,
        ).fetchone()

    # (g) Email xác nhận sinh viên + nhà trường (BR-14) — lỗi email KHÔNG làm payment fail
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
        pass  # đã SUCCESS — email thất bại chỉ ghi outbox FAILED ở notification-service

    return {
        "payment_id": payment_id, "status": "SUCCESS", "amount": amount,
        "student": {"student_id": row.student_id,
                    "full_name": payer.get("full_name", "")},
        "tuition_id": tuition_id, "balance_after": captured.get("balance_after"),
        "completed_at": _iso(completed.completed_at),
    }


# ------------------------- FR-05: gửi lại OTP -------------------------
@app.post("/payments/{payment_id}/resend-otp")
def resend_otp(payment_id: int, uid: int = Depends(require_uid)):
    """FR-05 — gửi lại mã OTP MỚI cho cùng payment (không tạo gd mới, không trừ tiền).

    Cho phép resend kể cả khi OTP cũ đã EXPIRED, miễn payment còn OTP_SENT và chưa quá
    `expires_at`. Throttle 30s tính từ lần sinh OTP gần nhất (last_otp_sent_at).
    """
    with connect("PaymentDB") as c:
        row = _load_payment(c, payment_id, uid)
        tuition_id, amount, status = int(row.tuition_id), int(row.amount), row.status
        expired = row.expires_at < _now_utc()
        last_sent = row.last_otp_sent_at
    if status != "OTP_SENT":
        raise state_conflict(f"Giao dịch không ở trạng thái chờ OTP (hiện: {status})")
    if expired:
        raise state_conflict("Giao dịch đã hết hạn, không gửi lại được mã — vui lòng tạo giao dịch mới")

    # (a) chống spam: tối đa 1 lần/30s mỗi payment → 429 RATE_LIMITED
    if last_sent is not None:
        waited = (_now_utc() - last_sent).total_seconds()
        if waited < RESEND_THROTTLE_SECONDS:
            remaining = int(RESEND_THROTTLE_SECONDS - waited) + 1
            raise rate_limited(f"Vui lòng chờ {remaining} giây nữa mới gửi lại được")

    # (b) sinh OTP mới (otp-service tự chuyển OTP ACTIVE cũ sang REPLACED)
    payer = _call("GET", f"{PAYER_URL}/internal/payers/{uid}", payment_id=payment_id)
    otp = _call("POST", f"{OTP_URL}/internal/otp/generate",
                {"uid": uid, "payment_id": payment_id, "email": payer["email"],
                 "purpose": "TUITION_PAYMENT"}, payment_id)
    # ghi mốc throttle NGAY khi sinh mã — kể cả email fail thì cũng không cho spam generate
    with connect("PaymentDB") as c:
        c.execute("UPDATE dbo.payments SET last_otp_sent_at = SYSUTCDATETIME() "
                  "WHERE payment_id = ?", payment_id)

    # (c) gửi email mã mới — lỗi KHÔNG hủy payment (OTP mới còn hiệu lực, user
    # gửi lại được sau khi hết throttle; payment tự chết theo expires_at nếu bỏ)
    try:
        _call("POST", f"{NOTIFICATION_URL}/internal/notifications/otp-email",
              {"payment_id": payment_id, "to_email": payer["email"],
               "to_name": payer["full_name"], "otp_code": otp["code"],
               "expires_in": 300}, payment_id)
    except AppError:
        raise service_unavailable(
            "Không gửi được email — mã mới đã sinh, vui lòng thử gửi lại sau ít giây")

    return {"payment_id": payment_id, "otp_expires_in_seconds": 300}


# ------------------------- FR-06: hủy giao dịch -------------------------
@app.post("/payments/{payment_id}/cancel")
def cancel_payment(payment_id: int, uid: int = Depends(require_uid)):
    """FR-06 — user hủy giao dịch đang chờ: dọn sạch mọi hệ quả (OTP, tuition, tiền).

    Chuyển CANCELLED TRƯỚC (conditional UPDATE — atomic claim chống race với
    verify-otp đang chạy song song), sau đó bù trừ từng bước idempotent.
    """
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
        # payment đã CANCELLED nhưng hệ quả chưa dọn xong — báo rõ để không tưởng nhầm
        raise service_unavailable(
            "Giao dịch đã hủy nhưng chưa dọn hết hệ quả: " + "; ".join(errors))
    return {"payment_id": payment_id, "status": "CANCELLED"}


# ------------------------- FR-07: lịch sử giao dịch -------------------------
@app.get("/payments")
def list_payments(status: str = "", page: int = 1, size: int = 20,
                  uid: int = Depends(require_uid)):
    """FR-07 — danh sách gd của CHÍNH user (uid từ JWT, client không truyền uid — BR-04).

    Lọc theo status + phân trang (size tối đa 100 — không load cả bảng).
    """
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
    """FR-07 — chi tiết 1 giao dịch (chỉ chủ sở hữu) + toàn bộ lịch sử FSM."""
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


# ------------------------- FR-08: job quét hết hạn -------------------------
def _sweep_once() -> None:
    """1 chu kỳ quét: OTP hết hạn → EXPIRED; payment quá hạn → dọn + EXPIRED."""
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
    """Kết thúc 1 payment quá hạn (BR-13/BR-15).

    Trường hợp đặc biệt — payment kẹt ở PROCESSING (crash giữa capture và PAID)
    mà tuition THỰC SỰ đã PAID: giao dịch đã thành công thật → hoàn tất SUCCESS
    thay vì hoàn tiền (hoàn tiền lúc này = mất tiền của nhà trường).
    """
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
        # chưa dọn xong — GIỮ nguyên trạng thái active để chu kỳ sau quét lại
        print(f"[sweep] payment {payment_id}: compensation pending {errors} - retry next cycle")
        return
    with connect("PaymentDB") as c:
        if _transition(c, payment_id, ("PENDING", "OTP_SENT", "PROCESSING"),
                       "EXPIRED", reason="Hết hạn — job quét hủy"):
            print(f"[sweep] payment {payment_id} -> EXPIRED (tuition {tuition_id} unlocked)")


def _sweep_loop() -> None:
    """Vòng lặp nền FR-08: chu kỳ 5–10s, lỗi từng giao dịch không làm chết job."""
    print(f"[sweep] sweeper started (interval {SWEEP_INTERVAL_SECONDS}s)")
    while True:
        try:
            _sweep_once()
        except Exception as exc:  # noqa: BLE001 — job nền phải sống qua mọi lỗi
            print(f"[sweep] cycle error: {exc!r}")
        time.sleep(SWEEP_INTERVAL_SECONDS)

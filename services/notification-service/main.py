"""notification-service (:8006) — gửi email OTP + email xác nhận thanh toán.

Kênh gửi: Gmail SMTP (App Password, TLS cổng 587) — docs/12 hướng dẫn tạo App Password.

Chính sách ghi outbox (docs/04 — NotificationDB):
    - Mọi email đều ghi 1 dòng vào email_outbox: PENDING → SENT (thành công) hoặc
      FAILED + last_error (SMTP lỗi).
    - Email xác nhận gửi cho sinh viên (PAYER) + CC nhà trường (SCHOOL) → 2 dòng outbox.

Chế độ DRY_RUN (để test không cần Gmail):
    - `NOTIFICATION_DRY_RUN=1` HOẶC chưa cấu hình `GMAIL_USER` → không gọi SMTP,
      vẫn ghi outbox với status SENT (dry run). Khi điền đủ GMAIL_USER +
      GMAIL_APP_PASSWORD vào .env là tự chuyển sang gửi thật.

Port mặc định: 8006. Chạy:
    python -m uvicorn main:app --port 8006 --app-dir services/notification-service --reload
"""
import re
import smtplib
import uuid
from email.message import EmailMessage

import pyodbc
from fastapi import Depends, FastAPI
from pydantic import BaseModel, Field

from shared import config
from shared.db import connect
from shared.errors import (
    install_error_handlers, service_unavailable, validation_error,
)
from shared.security import require_internal

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")   # kiểm tra đơn giản, không thêm thư viện

app = FastAPI(title="notification-service", version="1.0")
install_error_handlers(app)

GMAIL_USER = config.get_env("GMAIL_USER", "")
GMAIL_APP_PASSWORD = config.get_env("GMAIL_APP_PASSWORD", "")
MAIL_FROM_NAME = config.get_env("MAIL_FROM_NAME", "iBanking - TDTU")
DRY_RUN = config.get_int_env("NOTIFICATION_DRY_RUN", 0) == 1 or not GMAIL_USER
SMTP_HOST = config.get_env("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = config.get_int_env("SMTP_PORT", 587)
SMTP_TIMEOUT = config.get_int_env("SMTP_TIMEOUT_SECONDS", 15)


@app.get("/health")
def health():
    try:
        with connect("NotificationDB") as c:
            c.execute("SELECT 1").fetchone()
        return {
            "status": "ok", "service": "notification-service",
            "mode": "dry-run" if DRY_RUN else "smtp",
        }
    except pyodbc.Error:
        raise service_unavailable("Không kết nối được database NotificationDB")


# ------------------------- API nội bộ (payment-service gọi) -------------------------
class OtpEmailRequest(BaseModel):
    payment_id: int = Field(gt=0)
    to_email: str = Field(min_length=5, max_length=100)
    to_name: str = Field(min_length=1, max_length=100)
    otp_code: str = Field(min_length=6, max_length=6)
    expires_in: int = Field(default=300, gt=0, le=600)


class ConfirmEmailRequest(BaseModel):
    payment_id: int = Field(gt=0)
    to_email: str = Field(min_length=5, max_length=100)
    to_name: str = Field(min_length=1, max_length=100)
    cc_school_email: str = Field(min_length=5, max_length=100)
    amount: int = Field(gt=0)
    student_id: str = Field(min_length=1, max_length=20)
    tuition_id: int = Field(gt=0)
    completed_at: str = Field(min_length=4, max_length=40)


def _check_email(value: str, field: str) -> str:
    if not EMAIL_RE.match(value):
        raise validation_error(f"{field} không đúng định dạng email: {value}")
    return value


def _smtp_send(to_email: str, cc: list[str], subject: str, body: str) -> str:
    """Gửi 1 email qua Gmail SMTP. Trả về message_id (dry-run trả id giả có đánh dấu)."""
    if DRY_RUN:
        return f"dryrun-{uuid.uuid4().hex[:12]}"

    msg = EmailMessage()
    msg["From"] = f"{MAIL_FROM_NAME} <{GMAIL_USER}>"
    msg["To"] = to_email
    if cc:
        msg["Cc"] = ", ".join(cc)
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT) as smtp:
            smtp.starttls()
            smtp.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            smtp.send_message(msg)
    except (smtplib.SMTPException, OSError) as exc:
        raise _smtp_failure(str(exc))
    return f"smtp-{uuid.uuid4().hex[:12]}"


class _SmtpFailure(Exception):
    """Đánh dấu lỗi SMTP để caller ghi outbox FAILED rồi mới trả 503."""


def _smtp_failure(detail: str) -> _SmtpFailure:
    return _SmtpFailure(detail)


def _record_outbox(payment_id, to_email, recipient_type, template, subject, body,
                   status, message_id=None, error=None):
    """Ghi 1 dòng email_outbox (riêng transaction — email gửi rồi thì outbox phải có dòng)."""
    with connect("NotificationDB") as c:
        c.execute(
            "INSERT INTO dbo.email_outbox "
            "(payment_id, to_email, recipient_type, template, subject, body, status, "
            " attempts, last_error, sent_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, CASE WHEN ? = N'SENT' THEN SYSUTCDATETIME() END)",
            payment_id, to_email, recipient_type, template, subject, body,
            status, error, status,
        )


# ------------------------- Endpoint -------------------------
@app.post("/internal/notifications/otp-email")
def otp_email(body: OtpEmailRequest, _: None = Depends(require_internal)):
    """Email chứa mã OTP cho người nộp tiền (gọi khi tạo/resend giao dịch — FR-03/05)."""
    _check_email(body.to_email, "to_email")
    subject = f"[iBanking] Ma xac thuc OTP: {body.otp_code}"
    body_text = (
        f"Xin chao {body.to_name},\n\n"
        f"Ma xac thuc OTP de thanh toan hoc phi cua ban la:\n\n"
        f"    {body.otp_code}\n\n"
        f"Ma co hieu luc trong {body.expires_in // 60} phut "
        f"({body.expires_in} giay), chi dung cho giao dich "
        f"#{body.payment_id} va chi dung MOT lan.\n"
        f"Neu ban khong thuc hien giao dich nay, hay bo qua email.\n\n"
        f"Tran trong,\n{MAIL_FROM_NAME}"
    )
    try:
        message_id = _smtp_send(str(body.to_email), [], subject, body_text)
    except _SmtpFailure as exc:
        _record_outbox(body.payment_id, str(body.to_email), "PAYER", "OTP_EMAIL",
                       subject, body_text, "FAILED", error=str(exc))
        raise service_unavailable(f"Gửi email OTP thất bại: {exc}")

    _record_outbox(body.payment_id, str(body.to_email), "PAYER", "OTP_EMAIL",
                   subject, body_text, "SENT", message_id=message_id)
    return {"sent": True, "message_id": message_id, "dry_run": DRY_RUN}


@app.post("/internal/notifications/confirm-email")
def confirm_email(body: ConfirmEmailRequest, _: None = Depends(require_internal)):
    """Email xác nhận thanh toán thành công cho sinh viên + CC nhà trường (BR-14).

    Gửi 1 email với Cc nhà trường, ghi 2 dòng outbox (PAYER + SCHOOL).
    Lỗi SMTP -> ghi FAILED + 503, KHÔNG làm sập API (payment vẫn SUCCESS — lỗi email
    chỉ ảnh hưởng outbox, payment-service đã tách bạch).
    """
    _check_email(body.to_email, "to_email")
    _check_email(body.cc_school_email, "cc_school_email")
    amount_vn = f"{body.amount:,}".replace(",", ".")
    subject = f"[iBanking] Xac nhan thanh toan hoc phi thanh cong - GD #{body.payment_id}"
    body_text = (
        f"Xac nhan thanh toan hoc phi thanh cong\n"
        f"=====================================\n"
        f"Ma giao dich : #{body.payment_id}\n"
        f"Sinh vien    : {body.to_name} ({body.student_id})\n"
        f"Khoan hoc phi: #{body.tuition_id}\n"
        f"So tien      : {amount_vn} VND\n"
        f"Hoan tat luc : {body.completed_at}\n\n"
        f"Day la email tu dong, vui long khong tra loi.\n"
        f"{MAIL_FROM_NAME}"
    )
    try:
        message_id = _smtp_send(str(body.to_email), [str(body.cc_school_email)],
                                subject, body_text)
    except _SmtpFailure as exc:
        for rtype, mail in (("PAYER", str(body.to_email)), ("SCHOOL", str(body.cc_school_email))):
            _record_outbox(body.payment_id, mail, rtype, "CONFIRM_EMAIL",
                           subject, body_text, "FAILED", error=str(exc))
        raise service_unavailable(f"Gửi email xác nhận thất bại: {exc}")

    for rtype, mail in (("PAYER", str(body.to_email)), ("SCHOOL", str(body.cc_school_email))):
        _record_outbox(body.payment_id, mail, rtype, "CONFIRM_EMAIL",
                       subject, body_text, "SENT", message_id=message_id)
    return {"sent": True, "message_id": message_id, "dry_run": DRY_RUN}

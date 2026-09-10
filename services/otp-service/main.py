"""otp-service (:8005) — sinh và xác thực OTP 6 số gắn với từng giao dịch.

Chính sách lưu trữ (docs/04, FR-04, FR-05):
    - Bảng otps GIỮ LẠI bản ghi trong suốt vòng đời; status mô tả kết quả cuối:
      ACTIVE → USED (đúng) / LOCKED (sai đủ 5 lần) / EXPIRED (hết 5 phút) /
      CANCELLED (hủy giao dịch) / REPLACED (gửi lại mã mới).
    - Chỉ tác vụ dọn dữ liệu riêng mới xóa bản ghi terminal.

Bất biến bảo đảm bằng filtered unique index (db/02-schema.sql):
    - ux_otps_active_uid:     1 uid chỉ có 1 OTP ACTIVE
    - ux_otps_active_payment: 1 payment chỉ có 1 OTP ACTIVE
    - ux_otps_active_code:    mã ACTIVE không trùng mã ACTIVE khác (không trùng
      OTP đang có hiệu lực của giao dịch khác)

Port mặc định: 8005. Chạy:
    python -m uvicorn main:app --port 8005 --app-dir services/otp-service --reload
"""
import datetime as dt
import secrets

import pyodbc
from fastapi import Depends, FastAPI
from pydantic import BaseModel, Field

from shared import config
from shared.db import connect, is_unique_violation
from shared.errors import (
    install_error_handlers, otp_expired, otp_invalid, otp_locked, otp_used,
    service_unavailable, validation_error,
)
from shared.security import require_internal

app = FastAPI(title="otp-service", version="1.0")
install_error_handlers(app)

OTP_TTL_SECONDS = config.get_int_env("OTP_TTL_SECONDS", 300)   # BR-08: tối đa 5 phút
MAX_ATTEMPTS = config.get_int_env("OTP_MAX_ATTEMPTS", 5)       # BR-09: sai đủ 5 lần


def _now_utc() -> dt.datetime:
    """Now theo UTC, NAIVE — cùng chuẩn SYSUTCDATETIME() mà SQL Server trả về."""
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


@app.get("/health")
def health():
    try:
        with connect("OTPDB") as c:
            c.execute("SELECT 1").fetchone()
        return {"status": "ok", "service": "otp-service"}
    except pyodbc.Error:
        raise service_unavailable("Không kết nối được database OTPDB")


# ------------------------- API nội bộ (payment-service gọi) -------------------------
class GenerateRequest(BaseModel):
    uid: int
    payment_id: int = Field(gt=0)
    email: str = Field(min_length=3, max_length=100)
    purpose: str = "TUITION_PAYMENT"


class VerifyRequest(BaseModel):
    payment_id: int = Field(gt=0)
    code: str = Field(min_length=6, max_length=6)


class InvalidateRequest(BaseModel):
    payment_id: int = Field(gt=0)


@app.post("/internal/otp/generate")
def generate(body: GenerateRequest, _: None = Depends(require_internal)):
    """Chuyển OTP ACTIVE cũ của payment sang REPLACED rồi sinh mã mới — cùng 1 transaction.

    Mã mới sinh ngẫu nhiên 6 số (secrets); nếu trùng mã ACTIVE khác (vi phạm
    ux_otps_active_code) thì sinh lại — tối đa 5 lần.

    Lưu ý: KHÔNG raise lỗi bên trong `with connect()` — context manager sẽ rollback
    toàn bộ transaction (kể cả UPDATE REPLACED đã chạy đúng).
    """
    result = None
    with connect("OTPDB") as c:
        # 1) Vô hiệu hóa mã cũ (giữ lại bản ghi, đổi status): cả ACTIVE của payment này
        #    LẪN ACTIVE sót lại của cùng uid (bất biến ux_otps_active_uid: 1 uid 1 ACTIVE)
        c.execute(
            "UPDATE dbo.otps SET status = N'REPLACED', status_reason = N'THAY_THE_BOI_OTP_MOI', "
            "invalidated_at = SYSUTCDATETIME() "
            "WHERE status = N'ACTIVE' AND (payment_id = ? OR uid = ?)",
            body.payment_id, body.uid,
        )

        # 2) Sinh mã mới — thử lại khi trùng mã ACTIVE đang hiệu lực
        for _ in range(5):
            code = f"{secrets.randbelow(1000000):06d}"
            try:
                cur = c.execute(
                    "INSERT INTO dbo.otps (uid, payment_id, code, status, expires_at) "
                    "OUTPUT INSERTED.otp_id, INSERTED.expires_at "
                    "VALUES (?, ?, ?, N'ACTIVE', DATEADD(SECOND, ?, SYSUTCDATETIME()))",
                    body.uid, body.payment_id, code, OTP_TTL_SECONDS,
                )
                row = cur.fetchone()
            except pyodbc.IntegrityError as exc:
                if not is_unique_violation(exc):
                    raise
                continue   # trùng mã ACTIVE khác -> sinh lại mã khác
            result = {
                "otp_id": int(row.otp_id),
                "code": code,
                "expires_at": row.expires_at.isoformat() + "Z" if row.expires_at else None,
            }
            break

    if result is None:
        raise service_unavailable("Không sinh được mã OTP không trùng, thử lại sau")
    return result


@app.post("/internal/otp/verify")
def verify(body: VerifyRequest, _: None = Depends(require_internal)):
    """Xác thực OTP của 1 payment. Trả lỗi đúng mã theo trạng thái (docs/10).

    - Sai: attempts + 1 (status_reason=INVALID_CODE); đủ MAX_ATTEMPTS -> LOCKED
    - Hết hạn: cập nhật EXPIRED rồi trả OTP_EXPIRED
    - Đúng: cập nhật USED + used_at (BR-08: chỉ dùng thành công 1 lần)

    Lưu ý: các UPDATE trạng thái PHẢI được commit trước khi trả lỗi — nên lỗi
    được gom vào `err`, raise SAU khi `with connect()` kết thúc (exit sạch = commit).
    """
    if not body.code.isdigit():
        raise validation_error("Mã OTP phải gồm đúng 6 chữ số")

    err = None
    result = None
    with connect("OTPDB") as c:
        row = c.execute(
            "SELECT TOP 1 otp_id, code, status, attempts, expires_at "
            "FROM dbo.otps WHERE payment_id = ? ORDER BY otp_id DESC",
            body.payment_id,
        ).fetchone()
        if row is None:
            err = otp_invalid("Không tìm thấy OTP cho giao dịch này")
        elif row.status == "USED":
            err = otp_used()
        elif row.status == "LOCKED":
            err = otp_locked()
        elif row.status == "EXPIRED" or (row.status == "ACTIVE" and row.expires_at < _now_utc()):
            if row.status == "ACTIVE":
                c.execute(
                    "UPDATE dbo.otps SET status = N'EXPIRED', status_reason = N'HET_HAN' "
                    "WHERE otp_id = ? AND status = N'ACTIVE'",
                    row.otp_id,
                )
            err = otp_expired()
        elif row.status in ("CANCELLED", "REPLACED"):
            err = otp_invalid("Mã OTP đã bị vô hiệu hóa")
        elif not secrets.compare_digest(row.code, body.code):
            # sai mã — đếm lượt sai, đủ 5 lần khóa (BR-09)
            attempts = int(row.attempts) + 1
            if attempts >= MAX_ATTEMPTS:
                c.execute(
                    "UPDATE dbo.otps SET attempts = ?, status = N'LOCKED', "
                    "status_reason = N'SAI_QUA_SO_LAN' WHERE otp_id = ?",
                    attempts, row.otp_id,
                )
                err = otp_locked()
            else:
                c.execute(
                    "UPDATE dbo.otps SET attempts = ?, status_reason = N'INVALID_CODE' "
                    "WHERE otp_id = ?",
                    attempts, row.otp_id,
                )
                err = otp_invalid(detail=f"Còn {MAX_ATTEMPTS - attempts} lần thử")
        else:
            # đúng mã -> USED, đánh dấu dùng đúng 1 lần (BR-08)
            cur = c.execute(
                "UPDATE dbo.otps SET status = N'USED', used_at = SYSUTCDATETIME() "
                "WHERE otp_id = ? AND status = N'ACTIVE'",
                row.otp_id,
            )
            if cur.rowcount == 0:
                # 2 request verify song song: request đến sau thấy mã vừa bị USED
                err = otp_used()
            else:
                result = {"verified": True, "otp_id": int(row.otp_id)}

    if err is not None:
        raise err
    return result


@app.post("/internal/otp/invalidate")
def invalidate(body: InvalidateRequest, _: None = Depends(require_internal)):
    """Chuyển OTP ACTIVE của payment sang CANCELLED khi hủy giao dịch. Idempotent:
    không có bản ghi ACTIVE cũng trả 200."""
    with connect("OTPDB") as c:
        cur = c.execute(
            "UPDATE dbo.otps SET status = N'CANCELLED', status_reason = N'HUY_GIAO_DICH', "
            "invalidated_at = SYSUTCDATETIME() "
            "WHERE payment_id = ? AND status = N'ACTIVE'",
            body.payment_id,
        )
    updated = cur.rowcount > 0
    return {"updated": updated, "status": "CANCELLED" if updated else None}

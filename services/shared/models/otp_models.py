from datetime import datetime
from pydantic import BaseModel, Field


# =====================================================================
# READ MODELS (Query Models - Kết quả xác thực OTP trả về Client)
# =====================================================================

class OTPVerifyStatusReadModel(BaseModel):
    """
    Read Model kết quả xác nhận OTP cho UI.
    Khẳng định hợp lệ hay thất bại mà không lộ OTP thực sự.
    """
    payment_id: str
    is_valid: bool
    status: str  # VERIFIED | EXPIRED | INVALID | ALREADY_USED
    message: str


# =====================================================================
# WRITE MODELS (Command Models - Bảo mật mã OTP trong DB)
# =====================================================================

class OTPStoreWriteModel(BaseModel):
    """
    Write Model bảo mật mã OTP trong database (OTPDB).
    Ghi nhận hạn dùng (TTL max 5 phút) và trạng thái sử dụng độc nhất.
    """
    otp_id: str
    payment_id: str
    uid: int
    otp_code: str  # 6 chữ số
    status: str = "PENDING"  # PENDING | VERIFIED | EXPIRED
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)

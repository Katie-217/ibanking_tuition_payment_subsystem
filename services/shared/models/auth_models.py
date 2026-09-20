from datetime import datetime
from pydantic import BaseModel, Field


# =====================================================================
# READ MODELS (Query Models - Dữ liệu đọc công khai an toàn cho API/UI)
# =====================================================================

class UserPublicProfileReadModel(BaseModel):
    """
    Read Model công khai cho User Profile.
    Tuyệt đối không chứa password_hash hay thông tin credential nhạy cảm.
    """
    uid: int
    username: str
    full_name: str
    email: str
    phone: str | None = None
    role: str = "student"
    status: str = "ACTIVE"
    created_at: datetime | str | None = None


# =====================================================================
# WRITE MODELS (Command Models - Dữ liệu ghi/validate nghiệp vụ nội bộ)
# =====================================================================

class UserCredentialWriteModel(BaseModel):
    """
    Write Model bảo vệ dữ liệu xác thực (Credentials).
    Chỉ dùng trong Auth Service nội bộ để verify/chỉnh sửa mật khẩu.
    """
    uid: int
    password_hash: str
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class UserCreateWriteModel(BaseModel):
    """
    Write Model để khởi tạo sinh viên/user mới.
    """
    uid: int
    username: str
    full_name: str
    email: str
    phone: str | None = None
    role: str = "student"
    status: str = "ACTIVE"
    password: str

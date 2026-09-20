from datetime import datetime
from pydantic import BaseModel, Field


# =====================================================================
# READ MODELS (Query Models - Phục vụ hiển thị người nộp tiền & số dư)
# =====================================================================

class PayerProfileReadModel(BaseModel):
    """
    Read Model tổng hợp trả về cho API GET /payers/me.
    Gồm thông tin cá nhân và số dư khả dụng (VND).
    """
    payer_uid: int
    full_name: str
    phone: str | None = None
    email: str
    available_balance: float
    currency: str = "VND"


# =====================================================================
# WRITE MODELS (Command Models - Kiểm soát nghiêm ngặt biến động số dư)
# =====================================================================

class AccountBalanceWriteModel(BaseModel):
    """
    Write Model xử lý thay đổi số dư tài khoản.
    """
    account_id: int | str
    payer_uid: int
    available_balance: float = Field(..., ge=0, description="Số dư khả dụng không được âm")
    currency: str = "VND"
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class BalanceLedgerWriteModel(BaseModel):
    """
    Write Model ghi nhật ký giao dịch biến động số dư.
    """
    account_id: int | str
    payment_id: int | str
    change_type: str  # RESERVE | CAPTURE | RELEASE
    amount: float = Field(..., gt=0)
    balance_after: float
    created_at: datetime = Field(default_factory=datetime.utcnow)

from datetime import datetime
from pydantic import BaseModel, Field


# =====================================================================
# READ MODELS (Query Models - Biên lai giao dịch cho UI)
# =====================================================================

class PaymentReceiptReadModel(BaseModel):
    """
    Read Model biên lai thanh toán đã denormalize đầy đủ thông tin cho UI.
    """
    payment_id: str
    uid: int
    student_id: str
    student_name: str
    tuition_id: str
    school_name: str
    amount: float
    status: str  # PENDING | PROCESSING | COMPLETED | FAILED | CANCELLED
    created_at: datetime | str
    updated_at: datetime | str | None = None
    note: str | None = None


# =====================================================================
# WRITE MODELS (Command Models - Quản lý FSM & Lệnh thanh toán)
# =====================================================================

class PaymentCreateCommandWriteModel(BaseModel):
    """
    Write Command Model khi client khởi tạo thanh toán.
    """
    uid: int
    student_id: str
    tuition_id: str
    amount: float = Field(..., gt=0)


class PaymentStateWriteModel(BaseModel):
    """
    Write Model kiểm soát chuyển đổi trạng thái FSM giao dịch thanh toán.
    """
    payment_id: str
    uid: int
    student_id: str
    tuition_id: str
    amount: float
    status: str  # PENDING | PROCESSING | COMPLETED | FAILED | CANCELLED
    error_message: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

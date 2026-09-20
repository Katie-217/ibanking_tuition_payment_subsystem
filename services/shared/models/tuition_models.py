from datetime import datetime
from typing import List
from pydantic import BaseModel, Field


# =====================================================================
# READ MODELS (Query Models - Phiếu học phí tổng hợp sẵn cho UI)
# =====================================================================

class SubjectItemReadModel(BaseModel):
    subject_code: str
    subject_name: str
    credits: int
    amount: float


class TuitionBillReadModel(BaseModel):
    """
    Read Model denormalized cho phiếu học phí (GET /tuition/me).
    Nhúng đầy đủ thông tin sinh viên, trường nhận tiền và chi tiết các môn học.
    """
    tuition_id: str
    student_id: str
    student_name: str
    school_name: str
    finance_email: str
    beneficiary_name: str
    bank_name: str
    bank_account_no: str
    academic_year: str
    semester: str
    total_amount: float
    status: str  # UNPAID | PROCESSING | PAID
    items: List[SubjectItemReadModel] = []
    created_at: datetime | str | None = None


# =====================================================================
# WRITE MODELS (Command Models - Quản lý trạng thái học phí)
# =====================================================================

class TuitionStatusWriteModel(BaseModel):
    """
    Write Model cập nhật trạng thái đóng học phí.
    """
    tuition_id: str
    student_id: str
    status: str  # UNPAID | PROCESSING | PAID
    updated_at: datetime = Field(default_factory=datetime.utcnow)

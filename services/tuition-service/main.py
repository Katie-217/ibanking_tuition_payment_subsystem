"""tuition-service (:8003) — danh sách học phí + khóa/mở trạng thái nợ.

Port mặc định: 8003. Chạy:
    python -m uvicorn main:app --port 8003 --app-dir services/tuition-service --reload
"""
import datetime as dt

import pyodbc
from fastapi import Depends, FastAPI
from pydantic import BaseModel, Field

from shared.db import connect
from shared.errors import (
    forbidden, install_error_handlers, not_found, service_unavailable, state_conflict,
)
from shared.security import require_internal, require_uid

app = FastAPI(title="tuition-service", version="1.1")
install_error_handlers(app)


def _iso(value):
    """DATE/DATETIME2 -> chuỗi ISO cho JSON; NULL -> None."""
    return value.isoformat() if isinstance(value, (dt.date, dt.datetime)) else value


@app.get("/health")
def health():
    try:
        with connect("TuitionDB") as c:
            c.execute("SELECT 1").fetchone()
        return {"status": "ok", "service": "tuition-service"}
    except pyodbc.Error:
        raise service_unavailable("Không kết nối được database TuitionDB")


# ------------------------- API người dùng -------------------------
@app.get("/tuition/me")
def tuition_me(uid: int = Depends(require_uid)):
    """Hồ sơ sinh viên + DANH SÁCH HỌC KỲ của CHÍNH user — dữ liệu cho trang thanh toán (BR-04).

    Trả về mỗi học kỳ 1 dòng: số tiền, trạng thái, hạn nộp, NGÀY THANH TOÁN (paid_at).
    Chi tiết từng môn của 1 học kỳ: gọi GET /tuitions/{tuition_id}/items.
    """
    with connect("TuitionDB") as c:
        student = c.execute(
            """
            SELECT st.student_id, st.full_name, st.phone, st.email, st.enrollment_year,
                   sc.school_id, sc.name AS school_name,
                   fa.name AS faculty_name, fa.faculty_code,
                   ma.name AS major_name, ma.major_code, es.name AS system_name, es.system_code
            FROM dbo.students st
            JOIN dbo.schools sc     ON sc.school_id = st.school_id
            JOIN dbo.faculties fa   ON fa.faculty_id = st.faculty_id
            JOIN dbo.majors ma      ON ma.major_id = st.major_id
            JOIN dbo.edu_systems es ON es.system_id = st.system_id
            WHERE st.uid = ?
            """,
            uid,
        ).fetchone()

        tuitions = c.execute(
            """
            SELECT tuition_id, semester, amount, status, due_date, paid_at
            FROM dbo.tuitions
            WHERE student_id = ?
            ORDER BY due_date DESC
            """,
            student.student_id if student else None,
        ).fetchall() if student is not None else []

    if student is None:
        raise not_found("Không tìm thấy hồ sơ sinh viên cho tài khoản này")

    return {
        "student": {
            "student_id": student.student_id,
            "full_name": student.full_name,
            "phone": student.phone,
            "email": student.email,
            "enrollment_year": student.enrollment_year.strip() if student.enrollment_year else None,
            "school": {"id": student.school_id, "name": student.school_name},
            "faculty": {"code": student.faculty_code, "name": student.faculty_name},
            "major": {"code": student.major_code, "name": student.major_name},
            "edu_system": {"code": student.system_code.strip(), "name": student.system_name},
        },
        "tuitions": [
            {
                "tuition_id": int(t.tuition_id),
                "semester": t.semester,
                "amount": int(t.amount),
                "status": t.status,
                "due_date": _iso(t.due_date),
                "paid_at": _iso(t.paid_at),
            }
            for t in tuitions
        ],
    }


@app.get("/tuitions/{tuition_id}/enrollments")
def tuition_enrollments(tuition_id: int, uid: int = Depends(require_uid)):
    """CÁC MÔN SINH VIÊN ĐÃ ĐĂNG KÝ trong học kỳ đó + học phí từng môn + thông tin người nhận.

    Dữ liệu cho bảng môn học ở trang thanh toán và cho popup xác nhận.
    Chỉ trả về khi khoản học phí thuộc CHÍNH user đang đăng nhập (BR-04), người khác → 403.
    """
    with connect("TuitionDB") as c:
        head = c.execute(
            """
            SELECT tt.tuition_id, tt.semester, tt.amount, tt.status, tt.due_date, tt.paid_at,
                   st.student_id, st.full_name, st.email,
                   fa.name AS faculty_name, ma.name AS major_name,
                   sc.name AS school_name, sc.beneficiary_name, sc.bank_name, sc.bank_account_no
            FROM dbo.tuitions tt
            JOIN dbo.students st    ON st.student_id = tt.student_id
            JOIN dbo.schools sc     ON sc.school_id = st.school_id
            JOIN dbo.faculties fa   ON fa.faculty_id = st.faculty_id
            JOIN dbo.majors ma      ON ma.major_id = st.major_id
            WHERE tt.tuition_id = ? AND st.uid = ?
            """,
            tuition_id, uid,
        ).fetchone()

        if head is None:
            exists = c.execute("SELECT 1 FROM dbo.tuitions WHERE tuition_id = ?", tuition_id).fetchone()
            if exists is None:
                raise not_found(f"Không tìm thấy học phí {tuition_id}")
            raise forbidden("Học phí không thuộc về tài khoản này")

        items = c.execute(
            """
            SELECT e.subject_id, s.name AS subject_name, e.credits, e.amount, e.registered_at
            FROM dbo.enrollments e
            JOIN dbo.subjects s ON s.subject_id = e.subject_id
            WHERE e.tuition_id = ?
            ORDER BY e.subject_id
            """,
            tuition_id,
        ).fetchall()

    items_total = sum(int(i.amount) for i in items)
    return {
        "tuition": {
            "tuition_id": int(head.tuition_id),
            "semester": head.semester,
            "amount": int(head.amount),
            "status": head.status,
            "due_date": _iso(head.due_date),
            "paid_at": _iso(head.paid_at),
        },
        "student": {
            "student_id": head.student_id, "full_name": head.full_name, "email": head.email,
            "faculty_name": head.faculty_name, "major_name": head.major_name,
            "school_name": head.school_name,
        },
        "beneficiary": {
            "name": head.beneficiary_name, "bank_name": head.bank_name,
            "account_no": head.bank_account_no,
        },
        "enrollments": [
            {
                "subject_id": i.subject_id, "subject_name": i.subject_name,
                "credits": int(i.credits), "amount": int(i.amount),
                "registered_at": _iso(i.registered_at),
            }
            for i in items
        ],
        "total_credits": sum(int(i.credits) for i in items),
        "total_amount": items_total,
        # Cảnh báo dữ liệu: tổng học phí các môn đã đăng ký phải bằng số tiền học kỳ
        "amount_matches_enrollments": items_total == int(head.amount),
    }


# ------------------------- API nội bộ (payment-service gọi) -------------------------
class InternalAction(BaseModel):
    uid: int
    payment_id: int = Field(gt=0)


def _get_tuition(c: pyodbc.Connection, tuition_id: int, uid: int):
    """Lấy tuition + kiểm tra quyền sở hữu: uid phải khớp student_id (Case B — BR-04)."""
    row = c.execute(
        """
        SELECT tt.tuition_id, tt.student_id, tt.amount, tt.status, tt.paid_by_payment_id
        FROM dbo.tuitions tt
        JOIN dbo.students st ON st.student_id = tt.student_id
        WHERE tt.tuition_id = ? AND st.uid = ?
        """,
        tuition_id, uid,
    ).fetchone()
    if row is None:
        # phân biệt: không tồn tại vs không phải chủ sở hữu
        exists = c.execute("SELECT 1 FROM dbo.tuitions WHERE tuition_id = ?", tuition_id).fetchone()
        if exists is None:
            raise not_found(f"Không tìm thấy học phí {tuition_id}")
        raise forbidden("Học phí không thuộc về tài khoản này")
    return row


@app.get("/internal/tuitions/{tuition_id}")
def internal_get(tuition_id: int, uid: int, _: None = Depends(require_internal)):
    """payment-service lấy thông tin tuition để kiểm tra trước khi tạo giao dịch.

    Bao gồm full_name sinh viên + finance_email nhà trường (gửi email xác nhận BR-14).
    """
    with connect("TuitionDB") as c:
        row = c.execute(
            """
            SELECT tt.tuition_id, tt.student_id, st.full_name, tt.amount, tt.status,
                   sc.finance_email
            FROM dbo.tuitions tt
            JOIN dbo.students st ON st.student_id = tt.student_id
            JOIN dbo.schools sc ON sc.school_id = st.school_id
            WHERE tt.tuition_id = ? AND st.uid = ?
            """,
            tuition_id, uid,
        ).fetchone()
        if row is None:
            exists = c.execute("SELECT 1 FROM dbo.tuitions WHERE tuition_id = ?", tuition_id).fetchone()
            if exists is None:
                raise not_found(f"Không tìm thấy học phí {tuition_id}")
            raise forbidden("Học phí không thuộc về tài khoản này")
    return {
        "tuition_id": int(row.tuition_id),
        "student_id": row.student_id,
        "student_name": row.full_name,
        "amount": int(row.amount),
        "status": row.status,
        "finance_email": row.finance_email,
    }


@app.post("/internal/tuitions/{tuition_id}/lock")
def internal_lock(tuition_id: int, body: InternalAction, _: None = Depends(require_internal)):
    """Khóa tuition để bắt đầu thanh toán: UNPAID -> PAYING (Case B — chống thanh toán 2 lần song song)."""
    with connect("TuitionDB") as c:
        row = _get_tuition(c, tuition_id, body.uid)
        if row.status == "PAYING":
            raise state_conflict("Học phí đang được thanh toán bởi giao dịch khác")
        if row.status == "PAID":
            raise state_conflict("Học phí đã được thanh toán")
        cur = c.execute(
            "UPDATE dbo.tuitions SET status = N'PAYING' "
            "WHERE tuition_id = ? AND status = N'UNPAID'",
            tuition_id,
        )
        if cur.rowcount == 0:
            raise state_conflict("Trạng thái học phí vừa thay đổi, vui lòng thử lại")
    return {"tuition_id": tuition_id, "status": "PAYING"}


@app.post("/internal/tuitions/{tuition_id}/paid")
def internal_paid(tuition_id: int, body: InternalAction, _: None = Depends(require_internal)):
    """Đánh dấu đã nộp sau khi thanh toán thành công: PAYING -> PAID + lưu payment_id."""
    with connect("TuitionDB") as c:
        row = _get_tuition(c, tuition_id, body.uid)
        if row.status == "PAID" and int(row.paid_by_payment_id or 0) == body.payment_id:
            return {"tuition_id": tuition_id, "status": "PAID", "idempotent": True}
        if row.status == "PAID":
            raise state_conflict("Học phí đã được thanh toán bởi giao dịch khác")
        cur = c.execute(
            "UPDATE dbo.tuitions SET status = N'PAID', paid_by_payment_id = ?, "
            "paid_at = SYSUTCDATETIME() "
            "WHERE tuition_id = ? AND status = N'PAYING'",
            body.payment_id, tuition_id,
        )
        if cur.rowcount == 0:
            raise state_conflict("Học phí chưa ở trạng thái đang thanh toán (PAYING)")
    return {"tuition_id": tuition_id, "status": "PAID"}


@app.post("/internal/tuitions/{tuition_id}/release")
def internal_release(tuition_id: int, body: InternalAction, _: None = Depends(require_internal)):
    """Bù trừ khi giao dịch thất bại/hủy/hết hạn: PAYING -> UNPAID (bỏ payment_id nếu trùng)."""
    with connect("TuitionDB") as c:
        row = _get_tuition(c, tuition_id, body.uid)
        if row.status == "UNPAID":
            return {"tuition_id": tuition_id, "status": "UNPAID", "idempotent": True}
        cur = c.execute(
            "UPDATE dbo.tuitions SET status = N'UNPAID' "
            "WHERE tuition_id = ? AND status = N'PAYING'",
            tuition_id,
        )
        if cur.rowcount == 0:
            raise state_conflict("Học phí không ở trạng thái có thể hủy")
    return {"tuition_id": tuition_id, "status": "UNPAID"}
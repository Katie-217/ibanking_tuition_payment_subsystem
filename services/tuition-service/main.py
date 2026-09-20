import datetime as dt
from fastapi import Depends, FastAPI
from pydantic import BaseModel, Field

from shared.db import get_db
from shared.errors import (
    forbidden, install_error_handlers, not_found, service_unavailable, state_conflict,
)
from shared.security import require_internal, require_uid
from shared.models.tuition_models import TuitionBillReadModel, SubjectItemReadModel, TuitionStatusWriteModel

app = FastAPI(title="tuition-service", version="1.1")
install_error_handlers(app)


def _iso(value):
    if isinstance(value, (dt.date, dt.datetime)):
        return value.isoformat()
    return value


@app.get("/health")
def health():
    try:
        db = get_db("tuition_db")
        db.command("ping")
        return {"status": "ok", "service": "tuition-service", "database": "tuition_db (MongoDB)"}
    except Exception as e:
        raise service_unavailable(f"Không kết nối được MongoDB tuition_db: {str(e)}")


@app.get("/tuition/me")
def tuition_me(uid: int = Depends(require_uid)):
    db = get_db("tuition_db")
    auth_db = get_db("auth_db")

    user_doc = auth_db.users.find_one({"uid": uid})
    if not user_doc:
        raise not_found("Không tìm thấy người dùng")

    student_id = user_doc["username"]  # MSSV (vd: 521H0092)

    tuitions_cursor = db.tuitions.find({"student_id": student_id})
    tuition_list = list(tuitions_cursor)

    if not tuition_list:
        raise not_found(f"Không tìm thấy học phí cho sinh viên {student_id}")

    res_tuitions = []
    for t in tuition_list:
        res_tuitions.append({
            "tuition_id": str(t["tuition_id"]),
            "semester": t.get("semester", "Học kỳ 1"),
            "academic_year": t.get("academic_year", "2024-2025"),
            "amount": float(t["total_amount"]),
            "status": t["status"],
            "school_name": t.get("school_name", "Trường Đại học Tôn Đức Thắng"),
            "items": [
                {
                    "subject_code": i["subject_code"],
                    "subject_name": i["subject_name"],
                    "credits": int(i["credits"]),
                    "amount": float(i["amount"])
                }
                for i in t.get("items", [])
            ]
        })

    return {
        "student": {
            "student_id": student_id,
            "full_name": user_doc["full_name"],
            "email": user_doc["email"],
            "phone": user_doc.get("phone"),
        },
        "tuitions": res_tuitions
    }


@app.get("/tuitions/{tuition_id}/enrollments")
def tuition_enrollments(tuition_id: str, uid: int = Depends(require_uid)):
    db = get_db("tuition_db")
    auth_db = get_db("auth_db")

    user_doc = auth_db.users.find_one({"uid": uid})
    if not user_doc:
        raise forbidden("Tài khoản không hợp lệ")

    student_id = user_doc["username"]

    tuition = db.tuitions.find_one({"tuition_id": tuition_id})
    if not tuition:
        raise not_found(f"Không tìm thấy học phí {tuition_id}")

    if tuition["student_id"] != student_id:
        raise forbidden("Học phí không thuộc về tài khoản này")

    items = tuition.get("items", [])
    items_read = [
        SubjectItemReadModel(
            subject_code=i["subject_code"],
            subject_name=i["subject_name"],
            credits=int(i["credits"]),
            amount=float(i["amount"])
        )
        for i in items
    ]

    total_amount = sum(i.amount for i in items_read)

    return {
        "tuition": {
            "tuition_id": str(tuition["tuition_id"]),
            "semester": tuition.get("semester", "Học kỳ 1"),
            "amount": float(tuition["total_amount"]),
            "status": tuition["status"],
        },
        "student": {
            "student_id": student_id,
            "full_name": user_doc["full_name"],
            "email": user_doc["email"],
            "school_name": tuition.get("school_name", "Trường Đại học Tôn Đức Thắng"),
        },
        "beneficiary": {
            "name": tuition.get("beneficiary_name", "TRUONG DAI HOC TON DUC THANG"),
            "bank_name": tuition.get("bank_name", "VietinBank - CN Nam Sài Gòn"),
            "account_no": tuition.get("bank_account_no", "118000045678"),
        },
        "enrollments": [i.model_dump() for i in items_read],
        "total_credits": sum(i.credits for i in items_read),
        "total_amount": total_amount,
        "amount_matches_enrollments": total_amount == float(tuition["total_amount"]),
    }


class InternalAction(BaseModel):
    uid: int
    payment_id: str | int


@app.get("/internal/tuitions/{tuition_id}")
def internal_get(tuition_id: str, uid: int, _: None = Depends(require_internal)):
    db = get_db("tuition_db")
    auth_db = get_db("auth_db")

    user_doc = auth_db.users.find_one({"uid": uid})
    if not user_doc:
        raise forbidden("Không tìm thấy người dùng")

    student_id = user_doc["username"]

    tuition = db.tuitions.find_one({"tuition_id": tuition_id})
    if not tuition:
        raise not_found(f"Không tìm thấy học phí {tuition_id}")

    if tuition["student_id"] != student_id:
        raise forbidden("Học phí không thuộc về tài khoản này")

    return {
        "tuition_id": str(tuition["tuition_id"]),
        "student_id": student_id,
        "student_name": user_doc["full_name"],
        "amount": float(tuition["total_amount"]),
        "status": tuition["status"],
        "finance_email": tuition.get("finance_email", "tai-chinh@tdtu.edu.vn"),
    }


@app.post("/internal/tuitions/{tuition_id}/lock")
def internal_lock(tuition_id: str, body: InternalAction, _: None = Depends(require_internal)):
    db = get_db("tuition_db")
    tuition = db.tuitions.find_one({"tuition_id": tuition_id})
    if not tuition:
        raise not_found(f"Không tìm thấy học phí {tuition_id}")

    if tuition["status"] in ["PAYING", "PROCESSING"]:
        raise state_conflict("Học phí đang được thanh toán bởi giao dịch khác")
    if tuition["status"] == "PAID":
        raise state_conflict("Học phí đã được thanh toán")

    updated = db.tuitions.find_one_and_update(
        {"tuition_id": tuition_id, "status": "UNPAID"},
        {"$set": {"status": "PAYING", "updated_at": dt.datetime.utcnow()}},
        return_document=True
    )

    if not updated:
        raise state_conflict("Trạng thái học phí vừa thay đổi, vui lòng thử lại")

    return {"tuition_id": tuition_id, "status": "PAYING"}


@app.post("/internal/tuitions/{tuition_id}/paid")
def internal_paid(tuition_id: str, body: InternalAction, _: None = Depends(require_internal)):
    db = get_db("tuition_db")
    tuition = db.tuitions.find_one({"tuition_id": tuition_id})
    if not tuition:
        raise not_found(f"Không tìm thấy học phí {tuition_id}")

    payment_id_str = str(body.payment_id)
    if tuition["status"] == "PAID" and str(tuition.get("paid_by_payment_id", "")) == payment_id_str:
        return {"tuition_id": tuition_id, "status": "PAID", "idempotent": True}

    if tuition["status"] == "PAID":
        raise state_conflict("Học phí đã được thanh toán bởi giao dịch khác")

    updated = db.tuitions.find_one_and_update(
        {"tuition_id": tuition_id, "status": "PAYING"},
        {
            "$set": {
                "status": "PAID",
                "paid_by_payment_id": payment_id_str,
                "paid_at": dt.datetime.utcnow(),
                "updated_at": dt.datetime.utcnow()
            }
        },
        return_document=True
    )

    if not updated:
        raise state_conflict("Học phí chưa ở trạng thái đang thanh toán (PAYING)")

    return {"tuition_id": tuition_id, "status": "PAID"}


@app.post("/internal/tuitions/{tuition_id}/release")
def internal_release(tuition_id: str, body: InternalAction, _: None = Depends(require_internal)):
    db = get_db("tuition_db")
    tuition = db.tuitions.find_one({"tuition_id": tuition_id})
    if not tuition:
        raise not_found(f"Không tìm thấy học phí {tuition_id}")

    if tuition["status"] == "UNPAID":
        return {"tuition_id": tuition_id, "status": "UNPAID", "idempotent": True}

    updated = db.tuitions.find_one_and_update(
        {"tuition_id": tuition_id, "status": "PAYING"},
        {"$set": {"status": "UNPAID", "updated_at": dt.datetime.utcnow()}},
        return_document=True
    )

    if not updated:
        raise state_conflict("Học phí không ở trạng thái có thể hủy")

    return {"tuition_id": tuition_id, "status": "UNPAID"}

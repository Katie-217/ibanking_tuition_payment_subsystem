import datetime as dt
import secrets
from fastapi import Depends, FastAPI
from pydantic import BaseModel, Field

from shared import config
from shared.db import get_db
from shared.errors import (
    install_error_handlers, otp_expired, otp_invalid, otp_locked, otp_used,
    service_unavailable, validation_error,
)
from shared.security import require_internal
from shared.models.otp_models import OTPStoreWriteModel, OTPVerifyStatusReadModel

app = FastAPI(title="otp-service", version="1.0")
install_error_handlers(app)

OTP_TTL_SECONDS = config.get_int_env("OTP_TTL_SECONDS", 300)
MAX_ATTEMPTS = config.get_int_env("OTP_MAX_ATTEMPTS", 5)


def _now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


@app.get("/health")
def health():
    try:
        db = get_db("otp_db")
        db.command("ping")
        return {"status": "ok", "service": "otp-service", "database": "otp_db (MongoDB)"}
    except Exception as e:
        raise service_unavailable(f"Không kết nối được MongoDB otp_db: {str(e)}")


class GenerateRequest(BaseModel):
    uid: int
    payment_id: str | int
    email: str = Field(min_length=3, max_length=100)
    purpose: str = "TUITION_PAYMENT"


class VerifyRequest(BaseModel):
    payment_id: str | int
    code: str = Field(min_length=6, max_length=6)


class InvalidateRequest(BaseModel):
    payment_id: str | int


@app.post("/internal/otp/generate")
def generate(body: GenerateRequest, _: None = Depends(require_internal)):
    db = get_db("otp_db")
    payment_id_str = str(body.payment_id)

    # Vô hiệu hóa OTP cũ của giao dịch này hoặc uid này
    db.otps.update_many(
        {"status": "ACTIVE", "$or": [{"payment_id": payment_id_str}, {"uid": body.uid}]},
        {"$set": {"status": "REPLACED", "status_reason": "THAY_THE_BOI_OTP_MOI", "invalidated_at": _now_utc()}}
    )

    code = f"{secrets.randbelow(1000000):06d}"
    otp_id = f"OTP_{payment_id_str}_{secrets.token_hex(4)}"
    expires_at = _now_utc() + dt.timedelta(seconds=OTP_TTL_SECONDS)

    otp_model = OTPStoreWriteModel(
        otp_id=otp_id,
        payment_id=payment_id_str,
        uid=body.uid,
        otp_code=code,
        status="PENDING",
        expires_at=expires_at
    )

    doc = otp_model.model_dump()
    doc["status"] = "ACTIVE"
    doc["attempts"] = 0

    db.otps.insert_one(doc)

    return {
        "otp_id": otp_id,
        "code": code,
        "expires_at": expires_at.isoformat() + "Z"
    }


@app.post("/internal/otp/verify")
def verify(body: VerifyRequest, _: None = Depends(require_internal)):
    if not body.code.isdigit():
        raise validation_error("Mã OTP phải gồm đúng 6 chữ số")

    db = get_db("otp_db")
    payment_id_str = str(body.payment_id)

    # Tìm OTP mới nhất của payment_id
    doc = db.otps.find_one({"payment_id": payment_id_str}, sort=[("created_at", -1)])
    if not doc:
        raise otp_invalid("Không tìm thấy OTP cho giao dịch này")

    status = doc.get("status", "ACTIVE")
    expires_at = doc["expires_at"]
    attempts = doc.get("attempts", 0)

    if status == "USED":
        raise otp_used()
    if status == "LOCKED":
        raise otp_locked()
    if status == "EXPIRED" or (status == "ACTIVE" and expires_at < _now_utc()):
        if status == "ACTIVE":
            db.otps.update_one({"_id": doc["_id"]}, {"$set": {"status": "EXPIRED", "status_reason": "HET_HAN"}})
        raise otp_expired()
    if status in ["CANCELLED", "REPLACED"]:
        raise otp_invalid("Mã OTP đã bị vô hiệu hóa")

    if not secrets.compare_digest(doc["otp_code"], body.code):
        new_attempts = attempts + 1
        if new_attempts >= MAX_ATTEMPTS:
            db.otps.update_one({"_id": doc["_id"]}, {"$set": {"attempts": new_attempts, "status": "LOCKED", "status_reason": "SAI_QUA_SO_LAN"}})
            raise otp_locked()
        else:
            db.otps.update_one({"_id": doc["_id"]}, {"$set": {"attempts": new_attempts, "status_reason": "INVALID_CODE"}})
            raise otp_invalid(detail=f"Còn {MAX_ATTEMPTS - new_attempts} lần thử")

    # Mật khẩu khớp -> Cập nhật sang USED
    db.otps.update_one({"_id": doc["_id"], "status": "ACTIVE"}, {"$set": {"status": "USED", "used_at": _now_utc()}})

    read_model = OTPVerifyStatusReadModel(
        payment_id=payment_id_str,
        is_valid=True,
        status="VERIFIED",
        message="Xác thực OTP thành công"
    )
    return read_model.model_dump()


@app.post("/internal/otp/invalidate")
def invalidate(body: InvalidateRequest, _: None = Depends(require_internal)):
    db = get_db("otp_db")
    payment_id_str = str(body.payment_id)
    result = db.otps.update_many(
        {"payment_id": payment_id_str, "status": "ACTIVE"},
        {"$set": {"status": "CANCELLED", "status_reason": "HUY_GIAO_DICH", "invalidated_at": _now_utc()}}
    )
    updated = result.modified_count > 0
    return {"updated": updated, "status": "CANCELLED" if updated else None}


@app.post("/internal/otp/sweep-expired")
def sweep_expired(_: None = Depends(require_internal)):
    db = get_db("otp_db")
    result = db.otps.update_many(
        {"status": "ACTIVE", "expires_at": {"$lte": _now_utc()}},
        {"$set": {"status": "EXPIRED", "status_reason": "HET_HAN", "invalidated_at": _now_utc()}}
    )
    return {"expired": result.modified_count}

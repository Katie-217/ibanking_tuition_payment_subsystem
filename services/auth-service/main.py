import re
import bcrypt
from fastapi import Depends, FastAPI
from pydantic import BaseModel, Field

from shared import config
from shared.db import get_db
from shared.errors import (
    forbidden, install_error_handlers, invalid_credentials,
    not_found, service_unavailable, validation_error,
)
from shared.security import create_access_token, require_uid
from shared.models.auth_models import UserPublicProfileReadModel, UserCredentialWriteModel

app = FastAPI(title="auth-service", version="1.0")
install_error_handlers(app)

MSSV_RE = re.compile(r"^\d{3}[A-Za-z]\d{4}$", re.IGNORECASE)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=20)
    password: str = Field(min_length=1, max_length=100)


@app.get("/health")
def health():
    try:
        db = get_db("auth_db")
        db.command("ping")
        return {"status": "ok", "service": "auth-service", "database": "auth_db (MongoDB)"}
    except Exception as e:
        raise service_unavailable(f"Không kết nối được MongoDB auth_db: {str(e)}")


@app.post("/auth/login")
def login(body: LoginRequest):
    username_upper = body.username.strip().upper()
    if not MSSV_RE.match(username_upper):
        raise validation_error("Username phải đúng chuẩn MSSV TDTU (3 số + 1 chữ + 4 số)")

    db = get_db("auth_db")
    user_doc = db.users.find_one({"username": username_upper})
    if not user_doc:
        raise invalid_credentials()

    cred_doc = db.credentials.find_one({"uid": user_doc["uid"]})
    if not cred_doc:
        raise invalid_credentials()

    # Sử dụng Write Model để validate credential
    cred_model = UserCredentialWriteModel(**cred_doc)
    if not bcrypt.checkpw(body.password.encode("utf-8"), cred_model.password_hash.encode("utf-8")):
        raise invalid_credentials()

    # Sử dụng Read Model để trả về public profile
    user_read = UserPublicProfileReadModel(**user_doc)
    if user_read.status == "LOCKED":
        raise forbidden("Tài khoản đã bị khóa")

    return {
        "token": create_access_token(user_read.uid, user_read.username, user_read.role),
        "expires_in": config.JWT_EXPIRES_MINUTES * 60,
        "user": user_read.model_dump(),
    }


@app.post("/auth/logout")
def logout(uid: int = Depends(require_uid)):
    return {"message": "Đã đăng xuất"}


@app.get("/auth/me", response_model=UserPublicProfileReadModel)
def me(uid: int = Depends(require_uid)):
    db = get_db("auth_db")
    user_doc = db.users.find_one({"uid": uid})
    if not user_doc:
        raise not_found("Không tìm thấy người dùng")
    return UserPublicProfileReadModel(**user_doc)

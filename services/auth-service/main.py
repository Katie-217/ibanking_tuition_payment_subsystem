"""auth-service (:8001) — đăng nhập, cấp JWT, thông tin người dùng.

Port mặc định: 8001. Chạy:
    python -m uvicorn main:app --port 8001 --app-dir services/auth-service --reload
(với PYTHONPATH trỏ tới thư mục services/)
"""
import re

import bcrypt
import pyodbc
from fastapi import Depends, FastAPI
from pydantic import BaseModel, Field

from shared import config
from shared.db import connect
from shared.errors import (
    forbidden, install_error_handlers, invalid_credentials,
    not_found, service_unavailable, validation_error,
)
from shared.security import create_access_token, require_uid

app = FastAPI(title="auth-service", version="1.0")
install_error_handlers(app)

# MSSV TDTU: 3 số + 1 chữ + 4 số, vd 521H0092 (BR-01)
MSSV_RE = re.compile(r"^\d{3}[A-Za-z]\d{4}$")


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=20)
    password: str = Field(min_length=1, max_length=100)


def _check_db(c: pyodbc.Connection) -> None:
    c.execute("SELECT 1").fetchone()


@app.get("/health")
def health():
    try:
        with connect("AuthDB") as c:
            _check_db(c)
        return {"status": "ok", "service": "auth-service"}
    except pyodbc.Error:
        raise service_unavailable("Không kết nối được database AuthDB")


@app.post("/auth/login")
def login(body: LoginRequest):
    """Đăng nhập bằng username (MSSV TDTU) + password -> JWT. (BR-01, BR-02)"""
    if not MSSV_RE.match(body.username):
        raise validation_error("Username phải đúng chuẩn MSSV TDTU (3 số + 1 chữ + 4 số)")

    with connect("AuthDB") as c:
        row = c.execute(
            """
            SELECT u.uid, u.username, u.full_name, u.phone, u.email, u.role, u.status,
                   cr.password_hash
            FROM dbo.users u
            JOIN dbo.user_credentials cr ON cr.uid = u.uid
            WHERE u.username = ?
            """,
            body.username,
        ).fetchone()

        if row is None or not bcrypt.checkpw(body.password.encode("utf-8"), row.password_hash.encode("utf-8")):
            raise invalid_credentials()   # thông báo chung, không tiết lộ trường nào sai
        if row.status == "LOCKED":
            raise forbidden("Tài khoản đã bị khóa")

    return {
        "token": create_access_token(row.uid, row.username, row.role),
        "expires_in": config.JWT_EXPIRES_MINUTES * 60,
        "user": {"uid": row.uid, "username": row.username, "full_name": row.full_name, "role": row.role},
    }


@app.post("/auth/logout")
def logout(uid: int = Depends(require_uid)):
    """Stateless: frontend xóa token là xong; endpoint để đồng bộ flow UI."""
    return {"message": "Đã đăng xuất"}


@app.get("/auth/me")
def me(uid: int = Depends(require_uid)):
    with connect("AuthDB") as c:
        row = c.execute(
            "SELECT uid, username, full_name, phone, email, role, status FROM dbo.users WHERE uid = ?",
            uid,
        ).fetchone()
    if row is None:
        raise not_found("Không tìm thấy người dùng")
    return {
        "uid": row.uid, "username": row.username, "full_name": row.full_name,
        "phone": row.phone, "email": row.email, "role": row.role, "status": row.status,
    }
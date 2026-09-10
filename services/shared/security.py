"""Bảo mật chung: JWT + token nội bộ.

- JWT HS256, claims: uid, username, role, exp (mặc định 30 phút).
- Mọi service dùng chung JWT_SECRET -> service nào cũng tự đọc được uid
  mà không cần hỏi lại auth-service (stateless).
- Endpoint nội bộ (service gọi service) bắt buộc header X-Internal-Token.
"""
import hmac
import time

import jwt as pyjwt
from fastapi import Header

from . import config
from .errors import AppError, auth_required, forbidden

ALG = "HS256"


def create_access_token(uid: int, username: str, role: str = "student") -> str:
    now = int(time.time())
    payload = {
        "uid": uid,
        "username": username,
        "role": role,
        "iat": now,
        "exp": now + config.JWT_EXPIRES_MINUTES * 60,
    }
    return pyjwt.encode(payload, config.JWT_SECRET, algorithm=ALG)


def decode_token(token: str) -> dict:
    try:
        return pyjwt.decode(token, config.JWT_SECRET, algorithms=[ALG])
    except pyjwt.ExpiredSignatureError:
        raise auth_required("Phiên đăng nhập đã hết hạn, vui lòng đăng nhập lại")
    except pyjwt.InvalidTokenError:
        raise auth_required("Token không hợp lệ")


def _bearer_token(authorization: str) -> str:
    if not authorization.startswith("Bearer "):
        raise auth_required("Thiếu token đăng nhập (Authorization: Bearer <jwt>)")
    token = authorization[7:].strip()
    if not token:
        raise auth_required("Thiếu token đăng nhập")
    return token


def require_uid(authorization: str = Header(default="")) -> int:
    """FastAPI dependency: trả về uid lấy TỪ JWT (không bao giờ tin client)."""
    claims = decode_token(_bearer_token(authorization))
    try:
        return int(claims.get("uid"))
    except (TypeError, ValueError):
        raise auth_required("Token không chứa uid hợp lệ")


def require_internal(x_internal_token: str = Header(default="")) -> None:
    """FastAPI dependency cho endpoint nội bộ (service-to-service)."""
    if not hmac.compare_digest(x_internal_token.encode(), config.INTERNAL_TOKEN.encode()):
        raise forbidden("Thiếu token nội bộ hợp lệ (X-Internal-Token)")
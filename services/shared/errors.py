"""Chuẩn lỗi thống nhất cho toàn hệ thống.

Mọi service trả về cùng 1 envelope:
    {"error": {"code": "...", "message": "...", "detail": "..." (tùy chọn)}}
"""
import pyodbc
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    def __init__(self, status: int, code: str, message: str, detail=None):
        self.status = status
        self.code = code
        self.message = message
        self.detail = detail


# ---------- Factory lỗi nghiệp vụ (đồng bộ docs/03-thiet-ke-rest-api.md) ----------
def validation_error(message: str, detail=None) -> AppError:
    return AppError(400, "VALIDATION_ERROR", message, detail)


def invalid_credentials() -> AppError:
    return AppError(401, "AUTH_INVALID_CREDENTIALS", "Sai tên đăng nhập hoặc mật khẩu")


def auth_required(message: str = "Yêu cầu đăng nhập") -> AppError:
    return AppError(401, "AUTH_REQUIRED", message)


def forbidden(message: str = "Không có quyền thực hiện thao tác này") -> AppError:
    return AppError(403, "FORBIDDEN", message)


def not_found(message: str) -> AppError:
    return AppError(404, "NOT_FOUND", message)


def state_conflict(message: str) -> AppError:
    return AppError(409, "STATE_CONFLICT", message)


def insufficient_balance(required: int, available: int) -> AppError:
    return AppError(
        422, "INSUFFICIENT_BALANCE", "Số dư khả dụng không đủ để thanh toán",
        detail=f"required={required}, available={available}",
    )


def service_unavailable(message: str) -> AppError:
    return AppError(503, "SERVICE_UNAVAILABLE", message)


def install_error_handlers(app: FastAPI) -> None:
    """Gắn handler: AppError -> JSON envelope chuẩn; lỗi DB -> 500 an toàn."""

    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError):
        body = {"error": {"code": exc.code, "message": exc.message}}
        if exc.detail is not None:
            body["error"]["detail"] = exc.detail
        return JSONResponse(status_code=exc.status, content=body)

    @app.exception_handler(pyodbc.Error)
    async def _db_error(request: Request, exc: pyodbc.Error):
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "INTERNAL_ERROR", "message": "Lỗi truy cập database",
                               "detail": str(exc)}},
        )
"""api-gateway (:8000) — cổng vào DUY NHẤT của hệ thống cho frontend.

Trách nhiệm (docs/02, docs/03 mục 1.3):
    - Chuyển tiếp request sang đúng service theo tiền tố đường dẫn.
    - Kiểm tra JWT ngay tại gateway (hàng rào thứ nhất; service đích vẫn tự kiểm tra lại).
    - CORS cho trang web chạy local (http.server 5500, Live Server...).
    - GET /health tổng hợp trạng thái các service.

Nguyên tắc an toàn:
    - KHÔNG route bất kỳ đường nào bắt đầu bằng /internal — endpoint nội bộ chỉ được
      gọi trực tiếp giữa các service kèm X-Internal-Token (docs/03 mục 3).
    - Chỉ chuyển tiếp các header an toàn (Authorization, Idempotency-Key, Content-Type).

Port mặc định: 8000. Chạy:
    python -m uvicorn main:app --port 8000 --app-dir services/api-gateway --reload
"""
import asyncio

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from shared import config
from shared.errors import (
    AppError, auth_required, install_error_handlers, not_found, service_unavailable,
)
from shared.security import decode_token

app = FastAPI(title="api-gateway", version="1.0")
install_error_handlers(app)

# CORS: cho phép mọi trang chạy local (http://localhost:<cổng bất kỳ>) gọi vào gateway.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------- Cấu hình routing -------------------------
AUTH_URL        = config.get_env("AUTH_SERVICE_URL", "http://localhost:8001")
PAYER_URL       = config.get_env("PAYER_SERVICE_URL", "http://localhost:8002")
TUITION_URL     = config.get_env("TUITION_SERVICE_URL", "http://localhost:8003")
PAYMENT_URL     = config.get_env("PAYMENT_SERVICE_URL", "http://localhost:8004")
OTP_URL         = config.get_env("OTP_SERVICE_URL", "http://localhost:8005")
NOTIFICATION_URL = config.get_env("NOTIFICATION_SERVICE_URL", "http://localhost:8006")

UPSTREAM_TIMEOUT = config.get_int_env("UPSTREAM_TIMEOUT_SECONDS", 20)

# Tiền tố đường dẫn -> service đích (khớp docs/11 danh mục API).
ROUTE_TABLE = {
    "auth":        AUTH_URL,        # /auth/login, /auth/logout, /auth/me
    "payers":      PAYER_URL,       # /payers/me
    "tuition":     TUITION_URL,     # /tuition/me
    "tuitions":    TUITION_URL,     # /tuitions/{id}/enrollments
    "payments":    PAYMENT_URL,     # /payments... (payment-service)
}

# Đường KHÔNG cần JWT khi đi qua gateway (chỉ /auth/login; /health xử lý riêng).
PUBLIC_PATHS = {"/auth/login"}

# Header cho phép chuyển tiếp sang service đích (không forward toàn bộ header client).
FORWARD_HEADERS = ("authorization", "idempotency-key", "content-type")


@app.get("/health")
async def health():
    """Tổng hợp trạng thái từng service (docs/03 mục 2.12)."""
    targets = {
        "auth": AUTH_URL, "payer": PAYER_URL, "tuition": TUITION_URL,
        "payment": PAYMENT_URL, "otp": OTP_URL, "notification": NOTIFICATION_URL,
    }

    async def _check(client: httpx.AsyncClient, name: str, base_url: str) -> tuple:
        try:
            resp = await client.get(f"{base_url}/health")
            return name, "up" if resp.status_code == 200 else "down"
        except httpx.HTTPError:
            return name, "down"

    async with httpx.AsyncClient(timeout=3) as client:
        results = await asyncio.gather(*[_check(client, n, u) for n, u in targets.items()])
    services = {"gateway": "up", **dict(results)}
    all_up = all(v == "up" for v in services.values())
    return {"status": "ok" if all_up else "degraded", "services": services}


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy(path: str, request: Request):
    """Chuyển tiếp request sang service đích theo tiền tố đường dẫn."""
    full_path = "/" + path

    # Endpoint nội bộ không bao giờ lộ ra ngoài qua gateway.
    if full_path.startswith("/internal") or full_path.split("/")[1:2] == ["internal"]:
        raise not_found("Không tìm thấy đường dẫn này trên gateway")

    segment = path.split("/", 1)[0]
    base_url = ROUTE_TABLE.get(segment)
    if base_url is None:
        raise not_found(f"Không tìm thấy đường dẫn {full_path}")

    # Hàng rào JWT tại gateway (trừ đường công khai). Service đích vẫn tự kiểm tra lại.
    if full_path not in PUBLIC_PATHS:
        authorization = request.headers.get("authorization", "")
        if not authorization.startswith("Bearer "):
            raise auth_required("Thiếu token đăng nhập (Authorization: Bearer <jwt>)")
        decode_token(authorization[7:].strip())

    # Chỉ forward các header an toàn + body + query string nguyên vẹn.
    headers = {
        key: value for key, value in request.headers.items()
        if key.lower() in FORWARD_HEADERS and value
    }
    body = await request.body()

    try:
        async with httpx.AsyncClient(timeout=UPSTREAM_TIMEOUT) as client:
            resp = await client.request(
                request.method, f"{base_url}{full_path}",
                params=dict(request.query_params), headers=headers, content=body,
            )
    except httpx.HTTPError:
        raise service_unavailable(
            f"Service '{segment}' hiện không phản hồi — kiểm tra service đã khởi động chưa")

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        media_type=resp.headers.get("content-type"),
    )

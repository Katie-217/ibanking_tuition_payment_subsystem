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

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

AUTH_URL        = config.get_env("AUTH_SERVICE_URL", "http://127.0.0.1:8001")
PAYER_URL       = config.get_env("PAYER_SERVICE_URL", "http://127.0.0.1:8002")
TUITION_URL     = config.get_env("TUITION_SERVICE_URL", "http://127.0.0.1:8003")
PAYMENT_URL     = config.get_env("PAYMENT_SERVICE_URL", "http://127.0.0.1:8004")
OTP_URL         = config.get_env("OTP_SERVICE_URL", "http://127.0.0.1:8005")
NOTIFICATION_URL = config.get_env("NOTIFICATION_SERVICE_URL", "http://127.0.0.1:8006")

UPSTREAM_TIMEOUT = config.get_int_env("UPSTREAM_TIMEOUT_SECONDS", 20)

http_client = httpx.AsyncClient(timeout=UPSTREAM_TIMEOUT)


@app.on_event("shutdown")
async def _close_client():
    await http_client.aclose()

ROUTE_TABLE = {
    "auth":        AUTH_URL,
    "payers":      PAYER_URL,
    "tuition":     TUITION_URL,
    "tuitions":    TUITION_URL,
    "payments":    PAYMENT_URL,
}

PUBLIC_PATHS = {"/auth/login"}

FORWARD_HEADERS = ("authorization", "idempotency-key", "content-type")


@app.get("/health")
async def health():
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

    results = await asyncio.gather(*[_check(http_client, n, u) for n, u in targets.items()])
    services = {"gateway": "up", **dict(results)}
    all_up = all(v == "up" for v in services.values())
    return {"status": "ok" if all_up else "degraded", "services": services}


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy(path: str, request: Request):
    full_path = "/" + path

    if full_path.startswith("/internal") or full_path.split("/")[1:2] == ["internal"]:
        raise not_found("Không tìm thấy đường dẫn này trên gateway")

    segment = path.split("/", 1)[0]
    base_url = ROUTE_TABLE.get(segment)
    if base_url is None:
        raise not_found(f"Không tìm thấy đường dẫn {full_path}")

    if full_path not in PUBLIC_PATHS:
        authorization = request.headers.get("authorization", "")
        if not authorization.startswith("Bearer "):
            raise auth_required("Thiếu token đăng nhập (Authorization: Bearer <jwt>)")
        decode_token(authorization[7:].strip())

    headers = {
        key: value for key, value in request.headers.items()
        if key.lower() in FORWARD_HEADERS and value
    }
    body = await request.body()

    try:
        resp = await http_client.request(
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

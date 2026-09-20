# 12 — Thư viện & phần mềm cần cài để chạy dự án (MongoDB Edition)

> Mục tiêu: Sau khi làm theo hướng dẫn này, máy bạn chạy được **toàn bộ** dự án Microservices + MongoDB.

---

## 1. Phần mềm ngoài (cài 1 lần)

| # | Phần mềm | Dùng để làm gì | Link tải / ghi chú |
|---|---|---|---|
| 1 | **Python 3.11+** | Chạy mọi service FastAPI + scripts | https://www.python.org/downloads/ — khi cài **tick "Add python.exe to PATH"** |
| 2 | **MongoDB** (Local / Atlas / Docker) | Chứa 6 MongoDB databases của hệ thống | MongoDB Community Server / MongoDB Atlas Cloud / Docker Container |
| 3 | **MongoDB Compass** (tùy chọn) | Xem dữ liệu trực quan bằng giao diện GUI | https://www.mongodb.com/try/download/compass |
| 4 | **Docker Desktop** (tùy chọn) | Chạy tự động toàn bộ MongoDB + Seed data | https://www.docker.com/products/docker-desktop/ |
| 5 | **Git + tài khoản GitHub** | Quản lý mã nguồn | https://git-scm.com/downloads |

---

## 2. Thư viện Python (`services/requirements.txt`)

| Thư viện | Dùng ở đâu | Vì sao cần |
|---|---|---|
| `fastapi` | Tất cả 6 microservices + Gateway | Framework REST API async, tự sinh Swagger UI `/docs`, validate Pydantic |
| `uvicorn[standard]` | Web server ASGI | Server khởi chạy từng microservice |
| `pymongo` | `shared/db.py` — mọi service | Driver chính thức kết nối MongoDB (NoSQL) |
| `PyJWT` | `shared/security.py` | Tạo & xác thực JWT Token (HS256) |
| `bcrypt` | `auth-service` & seed script | Hash mật khẩu sinh viên (bcrypt) |
| `httpx` | `payment-service` & test scripts | Gọi API nội bộ service-to-service |
| `python-dotenv` | `shared/config.py` | Đọc biến môi trường từ file `.env` |

---

## 3. Cách cài đặt & Kiểm tra

### 3.1 Cài đặt thư viện Python
```bat
python -m pip install -r services\requirements.txt
```

### 3.2 Khởi tạo Dữ liệu & Kiểm tra Môi trường
```bat
# CÁCH 1: Dùng Docker Compose
docker compose up -d

# CÁCH 2: Dùng MongoDB Local
python scripts/init_mongodb.py
python scripts/check_env.py
```

Nếu màn hình báo `✅ Môi trường OK`, hệ thống đã sẵn sàng 100%!
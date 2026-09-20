# 08 — Hướng dẫn chạy test API (MongoDB & Docker Compose)

> Mục tiêu: Hướng dẫn chạy kiểm tra hệ thống API, khởi tạo Cơ sở dữ liệu MongoDB và khởi động hệ thống Microservices.

---

## 1. Điều kiện tiên quyết

| # | Mục | Yêu cầu |
|---|-----|---------|
| 1 | MongoDB | MongoDB Local hoặc Docker Desktop hoặc MongoDB Atlas |
| 2 | Python | Python 3.11 trở lên |
| 3 | Thư viện | `pip install -r services/requirements.txt` |
| 4 | Data Init | Chạy `python scripts/init_mongodb.py` hoặc `docker compose up -d` |

---

## 2. Cài đặt thư viện Python

```bat
rem Mở terminal tại thư mục gốc dự án:
pip install -r services\requirements.txt
```

Gói chính: `fastapi`, `uvicorn[standard]`, `pymongo` (kết nối MongoDB), `PyJWT` (JWT), `bcrypt` (hash mật khẩu), `httpx` (test API), `python-dotenv`.

---

## 3. Khởi tạo Database & Seed Data (Tự động 100%)

### Cách 1: Chạy bằng Docker Compose (Khuyên dùng khi làm nhóm)
```bash
docker compose up -d
```
Docker sẽ tự động khởi tạo MongoDB Server và tự nạp toàn bộ 6 Databases (`auth_db`, `payer_db`, `tuition_db`, `payment_db`, `otp_db`, `notification_db`) cùng 2 tài khoản thử nghiệm.

### Cách 2: Chạy trực tiếp qua Python script
```bash
python scripts/init_mongodb.py
```
Script sẽ khởi tạo 6 MongoDB Databases và nạp dữ liệu cho 2 tài khoản thử nghiệm:
- **`521H0092` - Võ Thị Thiên Kim** (15,000,000 VND / Học phí: 8,450,000 VND)
- **`523H0058` - Phạm Huỳnh Trịnh Nam** (20,000,000 VND / Học phí: 6,200,000 VND)
- **Mật khẩu thử nghiệm mặc định**: `Password123@`

---

## 4. Kiểm Tra Môi Trường (Check Environment)

Chạy script kiểm tra kết nối 6 MongoDB Databases và thư viện:
```bash
python scripts/check_env.py
```

Nếu màn hình hiện:
```text
================================================================
✅ Môi trường OK — Sẵn sàng khởi chạy Microservices!
================================================================
```
Hệ thống của bạn đã hoàn toàn sẵn sàng!
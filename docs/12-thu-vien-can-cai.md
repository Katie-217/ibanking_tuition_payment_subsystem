# 12 — Thư viện & phần mềm cần cài để chạy dự án

> Mục tiêu: sau khi làm theo file này, máy của bạn chạy được **toàn bộ** dự án
> (SQL Server → scripts → 3 service nền tảng → test API). Mục 1 là phần mềm ngoài,
> mục 2 là thư viện Python, mục 3 là cách cài đúng + kiểm tra.

---

## 1. Phần mềm ngoài (cài 1 lần)

| # | Phần mềm | Dùng để làm gì | Link tải / ghi chú |
|---|---|---|---|
| 1 | **Python 3.10+** | Chạy mọi service FastAPI + scripts | https://www.python.org/downloads/ — khi cài **tick "Add python.exe to PATH"** |
| 2 | **SQL Server** (Developer/Express) | Chứa 6 database của hệ thống | SQL Server 2022 Developer (miễn phí) — https://www.microsoft.com/sql-server |
| 3 | **SSMS** | Chạy script `db/01…03`, xem dữ liệu | https://learn.microsoft.com/sql/ssms/download-sql-server-management-studio-ssms |
| 4 | **ODBC Driver 18 for SQL Server** | Cầu nối Python ↔ SQL Server (bắt buộc) | https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server |
| 5 | **Git + tài khoản GitHub** | Quản lý nhánh, push, mở PR | https://git-scm.com/downloads — quy trình xem `docs/fr/00-quy-trinh-git.md` |
| 6 | **Excel/dbdiagram.io** (tùy chọn) | Xem sơ đồ quan hệ bảng | Dán `db/schema.dbml` vào https://dbdiagram.io |
| 7 | **Postman** (tùy chọn) | Test API tay | Không bắt buộc — mỗi service đã có sẵn Swagger UI `/docs` |
| 8 | **Tài khoản Gmail + App Password** | (Dùng sau, khi code notification-service) gửi email OTP/xác nhận | Bật 2-Step Verification → tạo App Password 16 ký tự → bỏ vào `.env` |

## 2. Thư viện Python (file `services/requirements.txt`)

| Thư viện | Tải bằng | Dùng ở đâu | Vì sao cần |
|---|---|---|---|
| `fastapi` | FastAPI | Tất cả 7 service | Framework viết REST API, tự sinh Swagger `/docs`, validate Pydantic |
| `uvicorn[standard]` | Uvicorn | Chạy từng service | Web server ASGI, hỗ trợ `--reload` khi code |
| `pyodbc` | pyodbc | `shared/db.py` — mọi service | Kết nối SQL Server, transaction (commit/rollback) |
| `PyJWT` | PyJWT | `shared/security.py` | Tạo + giải mã JWT HS256 cho đăng nhập |
| `bcrypt` | bcrypt | auth-service | Hash mật khẩu (lưu bảng `user_credentials`), chống lộ mật khẩu thô |
| `httpx` | httpx | payment-service gọi service khác; `scripts/test_api.py` | Gọi API service-to-service (REST) + viết test khói |
| `python-dotenv` | dotenv | `shared/config.py` | Đọc cấu hình từ file `.env` (DB, secret) không nhúng vào code |

> ⚠️ **Gói `jwt` (không viết hoa)** là gói rác trùng tên, gây lỗi import — nếu từng cài thì gỡ:
> `pip uninstall jwt`. Dự án chỉ dùng **PyJWT** (import `jwt`).

## 3. Cách cài đúng + kiểm tra

### 3.1 Khuyến khích: dùng môi trường ảo

```bat
rem mở terminal TẠI THƯ MỤC GỐC DỰ ÁN (thư mục chứa README.md)
python -m venv .venv
.venv\Scripts\activate          rem ▼ sau dòng này dấu nhắc hiện (.venv)
pip install -r services\requirements.txt
```

(Không muốn dùng venv thì bỏ qua 2 dòng đầu, nhưng venv tránh xung đột thư viện giữa các đồ án.)

### 3.2 Cài thư viện

```bat
python -m pip install --upgrade pip
python -m pip install -r services\requirements.txt
```

### 3.3 Kiểm tra đã cài đủ chưa

```bat
python scripts\check_env.py
```

Script sẽ kiểm tra: 7 gói Python → ODBC Driver 18 → file `.env` → kết nối 6 database →
mật khẩu bcrypt đã sinh. Kết quả mong đợi **toàn bộ ✅**.

```bat
python scripts\run_dev.bat     rem khởi động 3 service nền tảng
python scripts\test_api.py     rem 18/18 PASS = thư viện + môi trường chuẩn
```

## 4. Cấu hình liên quan đến thư viện

| File | Việc cần làm sau khi cài |
|---|---|
| `services\.env` | Copy từ `services\.env.example`, điền `DB_PWD` (mật khẩu sa), `JWT_SECRET`, `INTERNAL_TOKEN`; sau này thêm `GMAIL_APP_*` khi làm notification-service |
| `db\generate_password_hashes.py` | Sinh hash bcrypt cho mật khẩu demo `abc12345` (cần thư viện `bcrypt` trước) |

Nếu quên một thư viện nào, lỗi sẽ có dạng `ModuleNotFoundError: No module named 'xyz'`
→ vào 3.2 cài lại hoặc tra bảng mục 2 để biết gói cần tên chính xác là gì.
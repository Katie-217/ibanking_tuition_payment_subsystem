# iBanking – Phân hệ Đóng học phí (Microservices + REST API)

Đồ án giữa kỳ môn SOA: mô phỏng phân hệ đóng học phí của ứng dụng **iBanking** cho sinh viên **TDTU**.

- Người dùng đăng nhập bằng **username (MSSV chuẩn TDTU)** / **password** → nhận **JWT**.
- Dùng **số dư tài khoản của chính mình** để thanh toán **toàn bộ** khoản học phí **của chính mình** (không cho phép chọn sinh viên khác — xem *Project-Specific Decision*).
- Xác thực giao dịch bằng **OTP 6 số qua email** (hết hạn < 5 phút, 1 OTP gắn 1 giao dịch, chỉ dùng 1 lần).
- Sau khi giao dịch thành công: trừ số dư → học phí `PAID` → lưu lịch sử → gửi email xác nhận cho **sinh viên và nhà trường**.
- Đảm bảo **tính nhất quán** khi nhiều giao dịch đồng thời (lock tài khoản, lock khoản học phí, FSM trạng thái giao dịch, job quét tự hủy giao dịch quá hạn).

## Tech stack

| Thành phần | Công nghệ |
|---|---|
| Backend | Python 3.11+ / FastAPI + Uvicorn |
| Database | **MongoDB (NoSQL)** - 1 database riêng biệt cho từng service (Database-per-Service) |
| Architecture Pattern | Database-per-Service, **Selective CQRS (Read/Write Model Separation)**, Saga Orchestration, API Gateway |
| Email | Gmail SMTP (dùng App Password) |
| Authentication | JWT (HS256) |
| API access | `httpx` (service-to-service qua REST) |
| Container / Seeding | **Docker Compose** + `scripts/init_mongodb.py` tự động seed 100% data khi clone repo |

## Các microservice & MongoDB Databases

| Service | Port | Database (MongoDB) | Trách nhiệm chính & CQRS Models |
|---|---|---|---|
| api-gateway | 8000 | – | Điểm vào duy nhất, route, xác thực JWT, CORS |
| auth-service | 8001 | `auth_db` | Đăng nhập/logout, cấp & kiểm tra JWT (Selective CQRS: `UserPublicProfileReadModel`, `UserCredentialWriteModel`) |
| payer-service | 8002 | `payer_db` | Số dư, `GET /payers/me`, reserve/capture/release (Selective CQRS: `PayerProfileReadModel`, `AccountBalanceWriteModel`) |
| tuition-service | 8003 | `tuition_db` | Học phí, `GET /tuition/me`, lock/PAID/release (CQRS: `TuitionBillReadModel`, `TuitionStatusWriteModel`) |
| payment-service | 8004 | `payment_db` | Orchestrator thanh toán, FSM giao dịch, lịch sử (CQRS: `PaymentReceiptReadModel`, `PaymentStateWriteModel`) |
| otp-service | 8005 | `otp_db` | Tạo/xác thực OTP gắn với giao dịch (CQRS: `OTPVerifyStatusReadModel`, `OTPStoreWriteModel`) |
| notification-service | 8006 | `notification_db` | Gửi email OTP và email xác nhận (Gmail SMTP, lưu `email_logs`) |

## Tài khoản thử nghiệm (Test Accounts)

Khi clone dự án về, hệ thống tự động nạp 2 sinh viên thử nghiệm sau:
1. **Username / MSSV**: `521H0092` - **Võ Thị Thiên Kim** (Email: `521h0092@student.tdtu.edu.vn`, Số dư: `15.000.000 VND`, Học phí: `8.450.000 VND`)
2. **Username / MSSV**: `523H0058` - **Phạm Huỳnh Trịnh Nam** (Email: `523h0058@student.tdtu.edu.vn`, Số dư: `20.000.000 VND`, Học phí: `6.200.000 VND`)
- **Mật khẩu thử nghiệm mặc định**: `Password123@`

## Hướng dẫn chạy nhanh cho nhóm 2 người

```bash
# CÁCH 1: Chạy bằng Docker Compose (Khuyên dùng)
docker compose up -d

# CÁCH 2: Chạy trực tiếp với MongoDB Local hoặc Atlas
pip install -r services/requirements.txt
python scripts/init_mongodb.py
python scripts/check_env.py
```

## Cấu trúc thư mục

```
<thư-mục-gốc-dự-án>\
├── README.md                    ← file này
├── .gitignore                   ← chặn push .env, logs, __pycache__, .venv
├── .gitattributes               ← chuẩn hóa line-ending giữa các máy
├── docs\                        ← bộ tài liệu thiết kế chi tiết
│   ├── 01-lam-ro-yeu-cau.md         Làm rõ yêu cầu, scope, business rules
│   ├── 02-kien-truc-microservices.md Kiến trúc, sơ đồ, trách nhiệm service
│   ├── 03-thiet-ke-rest-api.md      Đặc tả REST API chi tiết từng endpoint
│   ├── 04-thiet-ke-co-so-du-lieu.md ERD + DDL SQL Server
│   ├── 05-luong-nghiep-vu-tuong-tac.md Sequence diagram từng chức năng
│   ├── 06-concurrency-fsm.md       FSM giao dịch + 2 case concurrency
│   ├── 07-huong-phat-trien-ke-hoach.md Hướng phát triển & kế hoạch triển khai
│   ├── 08-huong-dan-test-api.md     Hướng dẫn chạy test API (check_env, run_dev, test_api)
│   ├── 09-readme-bieu-dien-api-endpoint-lop.md Cách biểu diễn API trên frontend qua lớp endpoint
│   ├── 10-quy-dinh-ma-phan-hoi.md   Quy định mã HTTP + mã lỗi + trạng thái nghiệp vụ
│   ├── 11-tai-lieu-api-endpoint-resource.md Endpoint/resource là gì + DANH MỤC toàn bộ API
│   ├── 12-thu-vien-can-cai.md       Thư viện + phần mềm cần cài để chạy dự án
│   ├── 13-ke-hoach-trien-khai.md    Kế hoạch triển khai theo ngày (giai đoạn solo 10→17/09)
│   ├── NHAT-KY-CONG-VIEC.md         NHẬT KÝ + TIẾN ĐỘ: ai đã làm gì, cần cài gì để chạy
│   ├── PHAN-CONG-CONG-VIEC.md       PHÂN CÔNG Sprint 1: task từng người, output, ranh giới file
│   └── fr\                          ← TÀI LIỆU FR — mỗi chức năng 1 file
│       ├── 00-quy-trinh-git.md          Quy trình git: nhánh, conflict, push, PR, nhật ký
│       ├── FR-01-dang-nhap.md           Đăng nhập / đăng xuất
│       ├── FR-02-trang-chu.md           Trang chính (hồ sơ + số dư + học phí)
│       ├── FR-03-tao-giao-dich-gui-otp.md Tạo giao dịch & gửi OTP
│       ├── FR-04-xac-thuc-otp.md        Xác thực OTP & hoàn tất thanh toán
│       ├── FR-05-gui-lai-otp.md         Gửi lại OTP
│       ├── FR-06-huy-giao-dich.md       Hủy giao dịch đang chờ
│       ├── FR-07-lich-su-giao-dich.md   Lịch sử giao dịch
│       └── FR-08-job-quet-het-han.md    Job quét giao dịch hết hạn
├── db\                          ← script database (tự chạy trên SQL Server)
│   ├── 01-create-databases.sql     Tạo 6 database
│   ├── 02-schema.sql               Tạo toàn bộ bảng + constraint
│   ├── 03-seed.sql                 Dữ liệu demo (3 sinh viên)
│   ├── generate_password_hashes.py Sinh bcrypt hash cho mật khẩu demo
│   └── schema.dbml                 ERD dán vào tool xem quan hệ (dbdiagram.io)
├── frontend\                    ← mã nguồn web (giai đoạn sau)
│   └── js\
│       ├── endpoints.js            LỚP ENDPOINT: khai báo tập trung mọi URL API
│       └── api-client.js           Lớp gọi request (token, xử lý lỗi chuẩn)
├── services\                    ← mã nguồn từng service (giai đoạn 2)
│   ├── shared\                     config, db, errors, security dùng chung
│   ├── auth-service\               ĐÃ CODE: login/logout/me, JWT (:8001)
│   ├── payer-service\              ĐÃ CODE: /payers/me + trừ/hoàn tiền (:8002)
│   ├── tuition-service\            ĐÃ CODE: /tuition/me + khóa/PAID/release (:8003)
│   └── .env.example                mẫu cấu hình (copy thành .env)
├── scripts\                     ← công cụ chạy test
│   ├── check_env.py                kiểm tra môi trường trước khi test
│   ├── run_dev.bat                 khởi động 3 service nền tảng
│   └── test_api.py                 bộ test khói 18 test case
└── docker-compose.yml           ← khởi chạy toàn bộ hệ thống
```

> **Lớp endpoint (`frontend/js/endpoints.js`):** mọi trang JS gọi API qua `API_ENDPOINTS.<nhóm>.<tên>` — không bao giờ viết URL trực tiếp, khi backend đổi đường dẫn chỉ sửa 1 chỗ.

## Tài liệu

| # | Tài liệu | Nội dung |
|---|---|---|
| 1 | [Làm rõ yêu cầu](docs/01-lam-ro-yeu-cau.md) | Tổng hợp đề bài + file "làm rõ yêu cầu.txt", danh sách business rules, ràng buộc |
| 2 | [Kiến trúc Microservices](docs/02-kien-truc-microservices.md) | Sơ đồ kiến trúc, bảng trách nhiệm, nguyên tắc communication |
| 3 | [Thiết kế REST API](docs/03-thiet-ke-rest-api.md) | Đặc tả URI, method, input/output, status code, lỗi |
| 4 | [Thiết kế CSDL](docs/04-thiet-ke-co-so-du-lieu.md) | ERD + DDL SQL Server + constraint phục vụ concurrency |
| 5 | [Flow nghiệp vụ & tương tác services](docs/05-luong-nghiep-vu-tuong-tac.md) | Sequence diagram cho login, thanh toán, OTP, confirm, hủy, job quét |
| 6 | [Concurrency & FSM](docs/06-concurrency-fsm.md) | State machine giao dịch, xử lý 2 case đồng thời |
| 7 | [Hướng phát triển & kế hoạch](docs/07-huong-phat-trien-ke-hoach.md) | Milestone, checklist deliverables, mở rộng tương lai |
| 8 | [Hướng dẫn test API](docs/08-huong-dan-test-api.md) | Cách chạy 3 service nền tảng + bộ test tự động 18 case |
| 9 | [Biểu diễn API trên frontend (lớp endpoint)](docs/09-readme-bieu-dien-api-endpoint-lop.md) | Quy tắc dùng `API_ENDPOINTS` + `ApiClient`, không viết URL tay |
| 10 | [Quy định mã phản hồi](docs/10-quy-dinh-ma-phan-hoi.md) | Bảng HTTP status + mã lỗi nghiệp vụ + trạng thái enum + màu badge |
| 11 | [Endpoint & Resource + danh mục API](docs/11-tai-lieu-api-endpoint-resource.md) | Khái niệm + bảng toàn bộ API (Method · Endpoint · Ý nghĩa) |
| 12 | [Thư viện cần cài](docs/12-thu-vien-can-cai.md) | Python, ODBC, venv, pip, Gmail App Password |
| 13 | [Kế hoạch triển khai solo](docs/13-ke-hoach-trien-khai.md) | Lịch triển khai theo ngày 10→17/09, điều chỉnh quy trình 1 người, checklist tự review PR |
| FR | [Tài liệu FR theo chức năng](docs/fr/) | **Mỗi chức năng 1 file** (FR-01…FR-08) + [quy trình git](docs/fr/00-quy-trinh-git.md) |
| 📓 | [Nhật ký công việc](docs/NHAT-KY-CONG-VIEC.md) | Tiến độ + trạng thái + việc phải làm sau khi pull; **cập nhật khi bắt đầu và khi làm xong** |
| 📋 | [Phân công Sprint 1 (04→07/09)](docs/PHAN-CONG-CONG-VIEC.md) | Task từng người: mô tả, output cần tick, file được/không được sửa, mốc từng ngày |

## Bắt đầu test API ngay

```bat
pip install -r services\requirements.txt              rem 1) cài thư viện
python scripts\check_env.py                            rem 2) kiểm tra môi trường (DB, driver, .env)
scripts\run_dev.bat                                    rem 3) khởi động auth:8001 + payer:8002 + tuition:8003
python scripts\test_api.py                             rem 4) chạy 18 test case tự động
```

Chi tiết từng bước (tạo DB, sinh mật khẩu bcrypt, Swagger UI, curl): **[docs/08-huong-dan-test-api.md](docs/08-huong-dan-test-api.md)**.

## Demo nhanh (sau khi code xong)

1. Login: `POST /auth/login` với `{"username": "521H0092", "password": "..."}`
2. `GET /payers/me` + `GET /tuition/me` → hiển thị form thanh toán
3. `POST /payments` → nhận `payment_id`, hệ thống gửi OTP 6 số về email
4. `POST /payments/{id}/verify-otp` → trừ tiền, học phí PAID, gửi email xác nhận cho sinh viên + nhà trường
5. `GET /payments` → xem lịch sử giao dịch
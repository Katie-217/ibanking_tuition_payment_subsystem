# Tài liệu 02 — Kiến trúc Microservices

> Đáp ứng yêu cầu đề bài mục 1 (Use Case Diagram) và mục 2 (Microservices Architecture Diagram + trách nhiệm service + cách giao tiếp).

## 1. Use Case Diagram

### 1.1 Sơ đồ (PlantUML — dán vào https://www.plantuml.com/plantuml hoặc plugin PlantUML trên VS Code để render)

```plantuml
@startuml
left to right direction
skinparam actorStyle awesome

actor "Sinh viên TDTU (User)" as U
actor "Nhà trường (TDTU)" as S
actor "Hệ thống (Job định kỳ)" as T

rectangle "Phân hệ Đóng học phí iBanking" {
  usecase "Đăng nhập" as UC1
  usecase "Đăng xuất" as UC2
  usecase "Xem thông tin người nộp tiền" as UC3
  usecase "Xem thông tin học phí" as UC4
  usecase "Xem số dư khả dụng" as UC5
  usecase "Xác nhận thanh toán học phí" as UC6
  usecase "Nhận & nhập mã OTP" as UC7
  usecase "Xem kết quả giao dịch" as UC8
  usecase "Xem lịch sử giao dịch" as UC9
  usecase "Hủy giao dịch" as UC10
  usecase "Nhận email OTP" as UC11
  usecase "Nhận email xác nhận giao dịch" as UC12
  usecase "Tự hủy giao dịch quá hạn" as UC13
}

U --> UC1
U --> UC2
U --> UC3
U --> UC4
U --> UC5
U --> UC6
U --> UC7
U --> UC8
U --> UC9
U --> UC10
UC6 ..> UC11 : <<include>>\n(gửi OTP)
UC6 ..> UC12 : <<extend>>\n(khi thành công)
UC1 ..> UC3 : <<include>>\n(định danh uid)
U --> UC11
U --> UC12
S --> UC12
T --> UC13
@enduml
```

### 1.2 Đặc tả vắn tắt từng use case

| UC | Tên | Actor | Mô tả | Kết quả |
|---|---|---|---|---|
| UC1 | Đăng nhập | User | Nhập username (MSSV) + password | JWT |
| UC2 | Đăng xuất | User | Hủy phiên | Token bị xóa phía client |
| UC3 | Xem thông tin người nộp | User | `GET /payers/me` | Họ tên, SĐT, email (read-only) |
| UC4 | Xem thông tin học phí | User | `GET /tuition/me` | MSSV, họ tên SV, số tiền còn nợ |
| UC5 | Xem số dư | User | Một phần UC3 | Available balance |
| UC6 | Xác nhận thanh toán | User | Tạo payment + gửi OTP | Payment PENDING/OTP_SENT |
| UC7 | Nhập OTP | User | Xác thực OTP, xử lý trừ tiền | Payment SUCCESS/FAILED |
| UC8 | Xem kết quả | User | Nhận receipt | Mã giao dịch, số tiền, thời gian |
| UC9 | Xem lịch sử | User | `GET /payments` | Danh sách giao dịch |
| UC10 | Hủy giao dịch | User | Hủy payment đang chờ | Payment CANCELLED |
| UC11–12 | Nhận email | User / Nhà trường | Email OTP / xác nhận | Email đến hộp thư |
| UC13 | Tự hủy quá hạn | Job 5–10s | Quét payment hết hạn | Payment EXPIRED/CANCELLED |

## 2. Nguyên tắc kiến trúc

1. **Database per Service** — mỗi service sở hữu 1 database riêng; không service nào đọc/ghi thẳng DB của service khác.
2. **Giao tiếp chỉ qua REST API** giữa các service (đồng bộ, có timeout + retry có kiểm soát). Event/queue chỉ dùng nếu cần bất đồng bộ — ở phạm vi đồ án: không bắt buộc.
3. **API Gateway** là điểm vào **duy nhất** của client; service nội bộ không expose ra ngoài.
4. **Stateless** — mọi định danh nằm trong JWT; service không giữ session.
5. **Payment Service là orchestrator** — điều phối payer/tuition/otp/notification, sở hữu FSM giao dịch.
6. **Bảo mật 2 lớp** — JWT cho người dùng cuối; `X-Internal-Token` cho gọi nội bộ giữa các service.

## 3. Microservices Architecture Diagram

```mermaid
flowchart TB
    subgraph Client["Client (Web App)"]
        FE["Frontend Web<br/>(HTML/JS - trang Login,<br/>Thanh toán, OTP, Kết quả)"]
    end

    subgraph Edge["Lớp biên"]
        GW["API Gateway :8000<br/>- Route /auth /payers /tuition /payments<br/>- Verify JWT<br/>- CORS, rate-limit nhẹ"]
    end

    subgraph Core["Lớp dịch vụ nghiệp vụ"]
        AUTH["auth-service :8001<br/>login / logout / JWT / me"]
        PAYER["payer-service :8002<br/>GET /payers/me<br/>reserve / capture / release balance"]
        TUITION["tuition-service :8003<br/>GET /tuition/me<br/>lock / mark-paid / release tuition"]
        PAYMENT["payment-service :8004<br/>create / verify-otp / cancel<br/>FSM + lịch sử<br/>Job quét hết hạn 5-10s"]
        OTP["otp-service :8005<br/>generate / verify OTP<br/>6 số, <5 phút, 1 lần dùng"]
        NOTIF["notification-service :8006<br/>gửi email OTP<br/>email xác nhận cho SV + trường"]
    end

    subgraph Data["Database per Service (SQL Server)"]
        DB_AUTH[("AuthDB<br/>users, user_credentials")]
        DB_PAYER[("PayerDB<br/>payer, accounts, balance_ledger")]
        DB_TUITION[("TuitionDB<br/>schools, faculties, majors,<br/>edu_systems, students, tuitions")]
        DB_PAYMENT[("PaymentDB<br/>payments, payment_history")]
        DB_OTP[("OTPDB<br/>otps")]
        DB_NOTIF[("NotificationDB<br/>email_outbox")]
    end

    EXT["Gmail SMTP<br/>(App Password)"]

    FE -->|"HTTPS/JSON"| GW
    GW -->|"REST"| AUTH
    GW -->|"REST + JWT uid"| PAYER
    GW -->|"REST + JWT uid"| TUITION
    GW -->|"REST + JWT uid"| PAYMENT

    PAYMENT -->|"reserve/capture/release balance<br/>(X-Internal-Token)"| PAYER
    PAYMENT -->|"lock/mark-paid/release tuition<br/>(X-Internal-Token)"| TUITION
    PAYMENT -->|"generate/verify OTP<br/>(X-Internal-Token)"| OTP
    PAYMENT -->|"send otp-email / confirm-email<br/>(X-Internal-Token)"| NOTIF

    AUTH --> DB_AUTH
    PAYER --> DB_PAYER
    TUITION --> DB_TUITION
    PAYMENT --> DB_PAYMENT
    OTP --> DB_OTP
    NOTIF --> DB_NOTIF
    NOTIF -->|"SMTP TLS :587"| EXT
```

> **Ghi chú triển khai:** để đồ án gọn, các service chạy cùng 1 SQL Server instance, mỗi service có database riêng (schema database riêng biệt). Về nguyên tắc vẫn là Database-per-Service.

## 4. Trách nhiệm chi tiết từng service

### 4.1 auth-service (`:8001`)
| Hạng mục | Chi tiết |
|---|---|
| Endpoints ngoài | `POST /auth/login`, `POST /auth/logout`, `GET /auth/me` |
| Endpoints nội bộ | `POST /internal/verify-jwt` (gateway gọi khi xác thực request) |
| Nghiệp vụ | Kiểm tra username theo chuẩn MSSV TDTU; bcrypt verify password; cấp JWT HS256 (claims: `uid`, `username`, `role`, `exp` 30 phút); trả profile |
| Database | `AuthDB` |
| Ràng buộc | Password hash ở bảng `user_credentials` riêng, JOIN bằng `uid` |

### 4.2 payer-service (`:8002`)
| Hạng mục | Chi tiết |
|---|---|
| Endpoints ngoài | `GET /payers/me` |
| Endpoints nội bộ | `POST /internal/balance/reserve`, `POST /internal/balance/capture`, `POST /internal/balance/release` (nhận `payment_id`, `uid`, `amount`) |
| Nghiệp vụ | Chỉ trả thông tin payer tương ứng `uid` trong JWT; số dư set cứng từ seed; trừ tiền nguyên tử với row lock; ghi `balance_ledger` (reference `payment_id`) |
| Database | `PayerDB` |
| Ràng buộc | `CHECK (available_balance >= 0)`; capture = `UPDATE ... WHERE uid=@uid AND available_balance>=@amount` bọc trong transaction; idempotent theo `payment_id` |

### 4.3 tuition-service (`:8003`)
| Hạng mục | Chi tiết |
|---|---|
| Endpoints ngoài | `GET /tuition/me` |
| Endpoints nội bộ | `POST /internal/tuition/lock`, `POST /internal/tuition/paid`, `POST /internal/tuition/release` (nhận `payment_id`) |
| Nghiệp vụ | Từ `uid` → `student_id` → các tuitions `UNPAID` của chính sinh viên; chuyển trạng thái `UNPAID → PAYING → PAID`; đảm bảo 1 khoản chỉ PAID 1 lần |
| Quản lý | `schools` (trường), `faculties` (khoa), `majors` (ngành), `edu_systems` (hệ + mã hệ), `students` (bảng nhận diện MSSV), `tuitions` |
| Database | `TuitionDB` |
| Ràng buộc | Lock là `UPDATE tuitions SET status='PAYING' WHERE tuition_id=@id AND status='UNPAID'` — ai update 0 dòng là thua (case B concurrency); `CHECK status IN (...)` |

### 4.4 payment-service (`:8004`) — Orchestrator
| Hạng mục | Chi tiết |
|---|---|
| Endpoints ngoài | `POST /payments`, `GET /payments/{id}`, `GET /payments`, `POST /payments/{id}/verify-otp`, `POST /payments/{id}/cancel`, `POST /payments/{id}/resend-otp` |
| Nghiệp vụ | Sở hữu FSM: `PENDING → OTP_SENT → PROCESSING → SUCCESS/FAILED/CANCELLED/EXPIRED`; điều phối gọi payer/tuition/otp/notification theo đúng thứ tự; lưu history + snapshot từng bước; **job nền quét 5–10s** tự hủy giao dịch quá hạn |
| Database | `PaymentDB` |
| Ràng buộc | Đúng 1 payment active cho 1 (`uid`, `tuition_id`); idempotency; correlation id = `payment_id` đi kèm mọi call nội bộ |

### 4.5 otp-service (`:8005`)
| Hạng mục | Chi tiết |
|---|---|
| Endpoints nội bộ | `POST /internal/otp/generate` (nhận `uid`, `payment_id`, `email`), `POST /internal/otp/verify` (nhận `payment_id`, `code`) |
| Nghiệp vụ | Sinh OTP **6 chữ số** (dùng `secrets.randbelow`), expiry < 5 phút; verify: so code, kiểm tra hạn, giới hạn 5 lần sai; cập nhật `status` thành `EXPIRED`/`USED`/`LOCKED`/`REPLACED`, chỉ tác vụ dọn dữ liệu mới xóa bản ghi |
| Database | `OTPDB` |
| Ràng buộc | `UNIQUE (uid) WHERE status='ACTIVE'` và `UNIQUE (payment_id) WHERE status='ACTIVE'` → 1 OTP hiệu lực cho 1 tài khoản/1 giao dịch; code không trùng OTP ACTIVE khác; `CHECK (expires_at > created_at)` |

### 4.6 notification-service (`:8006`)
| Hạng mục | Chi tiết |
|---|---|
| Endpoints nội bộ | `POST /internal/notifications/otp-email`, `POST /internal/notifications/confirm-email` |
| Nghiệp vụ | Gửi email OTP cho người nộp; gửi email xác nhận cho **người nộp + nhà trường**; ghi `email_outbox` (retry nếu thất bại); template email tùy chỉnh |
| Database | `NotificationDB` |
| Ngoại kết nối | Gmail SMTP `smtp.gmail.com:587` (STARTTLS, App Password) |

### 4.7 api-gateway (`:8000`)
| Hạng mục | Chi tiết |
|---|---|
| Chức năng | Điểm vào duy nhất; kiểm tra JWT (gọi `auth-service`); chuyển tiếp request; CORS; log `payment_id`; cân bằng tạm thời bằng route tĩnh |
| Không làm | Không nắm business logic, không cache nghiệp vụ |

## 5. Cách thức giao tiếp giữa các service

### 5.1 Ma trận giao tiếp

| Từ \ Đến | auth | payer | tuition | payment | otp | notification |
|---|:--:|:--:|:--:|:--:|:--:|:--:|
| api-gateway | ✓ | ✓ | ✓ | ✓ | – | – |
| payment-service | – | ✓ | ✓ | – | ✓ | ✓ |
| Các service khác | – | – | – | – | – | – |

- Mũi tên nghiệp vụ đều **xuất phát từ payment-service** (orchestrator) — triệt tiêu vòng gọi chéo không kiểm soát.
- Mọi call nội bộ: header `X-Internal-Token` + `X-Correlation-Id: {payment_id}` + timeout 5s + retry tối đa 2 lần (chỉ retry cho idempotent call).

### 5.2 Quy ước giao tiếp đồng bộ (REST)

| Quy ước | Giá trị |
|---|---|
| Serialization | JSON, UTF-8 |
| Version | Tiền tố `/v1` nội bộ; đường ngoài giữ đúng đề (`/auth/login`, `/payers/me`, …) |
| Lỗi | Body chuẩn `{"error": {"code": "...", "message": "..."}}`, map đúng HTTP status |
| Timeout | 5 giây; 408/504 nếu quá hạn |
| Idempotency | Key theo `payment_id` cho balance capture, tuition state change, generate OTP |

### 5.3 Vì sao không dùng distributed transaction giữa các service

- Distributed transaction (2PC) quá nặng và chậm cho đồ án; thay vào đó dùng **Saga choreography đơn giản hóa** (orchestrator + bù trừ — compensating action):
  - Thành công: reserve balance → lock tuition → OTP → capture balance → tuition PAID → payment SUCCESS.
  - Thất bại ở bước nào: release/lỗi bù trừ các bước trước → payment FAILED → (tuỳ chọn) email thất bại.
- Tính nhất quán cuối cùng được đảm bảo bằng **job quét** đối chiếu payment với tuitions/accounts định kỳ.

## 6. Sơ đồ triển khai (deployment)

```mermaid
flowchart LR
    subgraph Host["1 máy (hoặc Docker Compose)"]
        G["api-gateway :8000"]
        A["auth-service :8001"]
        P["payer-service :8002"]
        T["tuition-service :8003"]
        PM["payment-service :8004<br/>+ job 5-10s"]
        O["otp-service :8005"]
        N["notification-service :8006"]
        DB[("SQL Server<br/>6 databases")]
    end
    B["Browser"] -->|"http://localhost:8000"| G
    G --> A & P & T & PM
    PM --> P & T & O & N
    N -.->|"SMTP :587"| SMTP["smtp.gmail.com"]
    A & P & T & PM & O & N --> DB
```

## 7. Ranh giới dữ liệu & định danh xuyên service

| Thực thể | Chủ sở hữu | Dùng ở service khác dưới dạng |
|---|---|---|
| `uid` (user) | auth-service | **Reference id** trong JWT (không tạo FK xuyên DB) |
| `student_id`, `tuition_id` | tuition-service | Reference id trong payment; payment luôn hỏi tuition-service để validate |
| `payment_id` | payment-service | Reference id trong PayerDB, OTPDB, NotificationDB |
| Email người nộp | payer-service | payment-service lấy qua `GET /payers/me` (nội bộ) rồi truyền cho otp/notification |

**Nguyên tắc:** reference bằng id + kiểm tra chéo qua API tại thời điểm xử lý — không bao giờ JOIN trực tiếp xuyên database.
# Tài liệu 07 — Hướng phát triển & Kế hoạch triển khai

> Kế thừa và bổ sung `plan phát triển.txt`. Tài liệu này chốt **phạm vi code giai đoạn 2**, thứ tự xây dựng, cấu trúc mã nguồn và checklist nộp bài.

## 1. Những bổ sung so với plan phát triển.txt (đã chốt cùng người dùng)

| # | Bổ sung | Lý do / nguồn |
|---|---|---|
| 1 | **Self-payment only** — không cho truyền id từ client, mọi định danh từ JWT uid | Project-Specific Decision |
| 2 | Password hash lưu bảng `user_credentials` riêng, nối `users` qua uid; username chuẩn MSSV TDTU + quan hệ student ↔ school trong DB | làm rõ yêu cầu.txt |
| 3 | OTP giữ bản ghi cùng `status`: unique `uid`, `payment_id`, `code` chỉ áp dụng khi `status = ACTIVE`; hết hạn / đã dùng / hủy GD → cập nhật status terminal, tác vụ dọn dữ liệu mới xóa | yêu cầu cập nhật 06/09/2026 |
| 4 | FSM 7 trạng thái + bảng transition hợp lệ + payment_history | plan + làm rõ yêu cầu |
| 5 | **Job quét 5–10s** tự hủy GD quá hạn (OTP hết hạn, >5 phút, kẹt trạng thái) | làm rõ yêu cầu.txt |
| 6 | Gửi email xác nhận cho **sinh viên + nhà trường** khi thành công (không chỉ người nộp) | làm rõ yêu cầu.txt |
| 7 | Gửi mail bằng **Gmail SMTP thật** (App Password), template email tùy chỉnh; outbox + retry | làm rõ + quyết định stack |
| 8 | Idempotency-key cho `POST /payments`; ledger unique `(payment_id, change_type)` | kỹ thuật REST chuẩn, chống retry kép |
| 9 | `ux_payments_success` (filtered unique) ở PaymentDB — chặn double-pay ngay tầng DB | đảm bảo case B concurrency |
| 10 | Rate-limit resend OTP (1 lần/30s) + khóa OTP sau 5 lần nhập sai | an toàn giao dịch |
| 11 | Tài liệu + diagram hoàn chỉnh trong `docs/` (7 tài liệu) | yêu cầu đề bài mục 1–3, 8 |

## 2. Cấu trúc mã nguồn dự kiến (giai đoạn 2)

```
services/
├── shared/                     # thư viện dùng chung (không phải service)
│   ├── errors.py               # chuẩn error envelope + mã lỗi
│   ├── http.py                 # httpx client + internal token + timeout/retry
│   └── config.py               # đọc env dùng chung
├── api-gateway/            :8000
│   ├── main.py                 # FastAPI app, CORS, route tĩnh
│   ├── auth_middleware.py      # verify JWT -> gắn X-Auth-Uid
│   └── routes.py
├── auth-service/           :8001   -> AuthDB
│   ├── main.py, models.py, schemas.py
│   ├── routes/auth.py, routes/internal.py
│   └── security.py              # bcrypt + PyJWT
├── payer-service/          :8002   -> PayerDB
│   ├── main.py, routes/payers.py, routes/internal.py
│   ├── services/balance.py      # capture/release + ledger (UPDLOCK)
│   └── db.py
├── tuition-service/        :8003   -> TuitionDB
│   ├── main.py, routes/tuition.py, routes/internal.py
│   └── services/tuition_state.py # lock/paid/release (conditional update)
├── payment-service/        :8004   -> PaymentDB
│   ├── main.py, routes/payments.py
│   ├── orchestrator.py          # saga: lock->otp->send->verify->capture->paid
│   ├── fsm.py                   # bảng transition hợp lệ
│   ├── sweep.py                 # background job 5-10s
│   └── db.py
├── otp-service/            :8005   -> OTPDB
│   ├── main.py, routes/internal.py
│   └── services/otp.py          # secrets.randbelow + constraints
├── notification-service/   :8006   -> NotificationDB
│   ├── main.py, routes/internal.py
│   ├── mailer.py                # smtplib -> smtp.gmail.com:587
│   ├── templates/otp_email.html
│   ├── templates/confirm_email.html
│   └── outbox.py                # ghi outbox + retry
├── frontend/                (Web app tĩnh phục vụ bởi gateway hoặc live-server)
│   ├── index.html (login), payment.html, otp.html, result.html, history.html
│   └── js/api.js                # gọi gateway, xử lý 401/409/422
├── db/
│   ├── 01-create-databases.sql
│   ├── 02-schema-per-db.sql     # DDL trong tài liệu 04
│   ├── 03-seed.sql
│   └── seed_bcrypt.py           # sinh hash bcrypt cho mật khẩu demo
├── scripts/
│   ├── run_all.sh / run_all.bat
│   └── concurrency_test.py      # kịch bản 1,2 (song song)
├── .env.example                 # connection strings, JWT secret, SMTP...
└── docker-compose.yml           # (tùy chọn) 7 service + SQL Server container
```

**Nguyên tắc code:**
- Mỗi service là 1 FastAPI app độc lập, cùng chuẩn Pydantic schema, cùng error envelope.
- Không import chéo database; mọi liên kết qua HTTP nội bộ.
- Mỗi service có `.env` riêng (port, connection string, internal token, SMTP cho notification).

## 3. Milestone triển khai (thứ tự thực hiện)

| GĐ | Nội dung | Deliverable | Trạng thái |
|---|---|---|---|
| 0 | Làm rõ yêu cầu + thiết kế | Bộ tài liệu `docs/01..07` + README | ✅ xong |
| 1 | DB: chạy DDL + seed (6 database) | `db/*.sql` + data demo | ⬜ tiếp theo |
| 2 | shared lib + auth-service (JWT, login) | chạy được login trên :8001 | ⬜ |
| 3 | payer-service + tuition-service (`/me` + internal lock/capture) | gọi được qua gateway | ⬜ |
| 4 | otp-service + notification-service (Gmail SMTP) | nhận được email OTP thật | ⬜ |
| 5 | payment-service: orchestrator + FSM + history + sweep job | luồng thanh toán đầy đủ | ⬜ |
| 6 | api-gateway nối toàn bộ + kiểm tra bảo mật (uid từ JWT) | 1 cổng vào duy nhất | ⬜ |
| 7 | Frontend web (login → thanh toán → OTP → kết quả → lịch sử) | demo được trên browser | ⬜ |
| 8 | Concurrency test (kịch bản 1, 2) + fix | bằng chứng 2 case đề bài | ⬜ |
| 9 | Tài liệu cài đặt & hướng dẫn chạy + video/ghi hình demo | README + slides | ⬜ |

## 4. Biến môi trường từng service (`.env.example`)

```env
# ===== auth-service =====
AUTH_PORT=8001
AUTH_DB_CONN=mssql+pyodbc://sa:Password123!@localhost:1433/AuthDB?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes
JWT_SECRET=change-me-strong-secret
JWT_EXPIRES_MINUTES=30

# ===== payer-service =====
PAYER_PORT=8002
PAYER_DB_CONN=mssql+pyodbc://sa:Password123!@localhost:1433/PayerDB?driver=...

# ===== tuition-service =====
TUITION_PORT=8003
TUITION_DB_CONN=mssql+pyodbc://sa:Password123!@localhost:1433/TuitionDB?driver=...

# ===== payment-service =====
PAYMENT_PORT=8004
PAYMENT_DB_CONN=mssql+pyodbc://sa:Password123!@localhost:1433/PaymentDB?driver=...
PAYER_SERVICE_URL=http://localhost:8002
TUITION_SERVICE_URL=http://localhost:8003
OTP_SERVICE_URL=http://localhost:8005
NOTIFICATION_SERVICE_URL=http://localhost:8006
PAYMENT_SWEEP_INTERVAL=7
PAYMENT_TTL_SECONDS=300

# ===== otp-service =====
OTP_PORT=8005
OTP_DB_CONN=mssql+pyodbc://sa:Password123!@localhost:1433/OTPDB?driver=...
OTP_TTL_SECONDS=300
OTP_MAX_ATTEMPTS=5

# ===== notification-service =====
NOTIF_PORT=8006
NOTIF_DB_CONN=mssql+pyodbc://sa:Password123!@localhost:1433/NotificationDB?driver=...
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your.email@gmail.com
SMTP_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx   # Gmail App Password (bật 2FA)
SCHOOL_FINANCE_EMAIL=hocphi@tdtu.edu.vn

# ===== chung =====
INTERNAL_TOKEN=shared-secret-between-services
```

> **Gmail App Password:** vào Google Account → Security → 2-Step Verification → App passwords → tạo 1 password cho app "Mail". Nếu không muốn gửi thật khi dev, đặt `SMTP_MOCK=true` (sẽ bổ sung chế độ mock ghi email vào outbox để vẫn demo được).

## 5. Checklist đối chiếu yêu cầu đề bài (8 mục)

| # | Yêu cầu đề | Hoàn thành bởi |
|---|---|---|
| 1 | Phân tích nghiệp vụ + Use Case + ERD | docs 01 (phân tích), 02 §1 (Use Case), 04 §1 (ERD) |
| 2 | Kiến trúc Microservices + trách nhiệm + giao tiếp | docs 02 §3, §4, §5 |
| 3 | REST API: URI, method, input, output, status code | docs 03 (đầy đủ + nội bộ) |
| 4 | Thiết kế & hiện thực DB SQL/NoSQL | docs 04 (DDL SQL Server) + sẽ code GĐ1 |
| 5 | Lập trình service + API đủ luồng nghiệp vụ | GĐ 2–6 (code) |
| 6 | Transaction & concurrency (2 case) | docs 06 + GĐ 8 test |
| 7 | Giao diện Web tích hợp API | GĐ 7 |
| 8 | Tài liệu + hướng dẫn cài đặt, chạy, sử dụng | README + docs 07 + slide demo |

## 6. Điểm cần lưu ý khi bảo vệ (gợi ý giải thích)

1. **Tại sao Payment Service phải là orchestrator?** — mọi thay đổi trạng thái giao dịch tập trung 1 chỗ, tránh vòng gọi chéo giữa payer↔tuition, dễ kiểm soát FSM và bù trừ.
2. **Tại sao không dùng distributed transaction?** — 2PC chậm, khóa lâu; Saga + conditional update + job quét vừa đủ đảm bảo eventual consistency cho đồ án.
3. **Chống dư âm như nào?** — UPDATE có điều kiện `balance >= amount` trong transaction + CHECK ràng buộc + ledger unique idempotency.
4. **Chống double-pay như nào?** — 3 tầng: conditional lock `UNPAID→PAYING`, unique `ux_payments_success`, check lại trạng thái ở mọi bước.
5. **OTP đảm bảo gì?** — 6 số (secrets), TTL < 5 phút, 1 payment 1 OTP ACTIVE (filtered unique), code ACTIVE không trùng (filtered unique), verify 1 lần (conditional update), khóa sau 5 lần sai.

## 7. Hướng phát triển tương lai (ngoài phạm vi giữa kỳ)

- Chuyển internal call sang message queue (RabbitMQ/Kafka) + Outbox pattern cho notification.
- Refresh token / Redis blacklist cho logout thật sự.
- Thêm API phía trường (dashboard đối soát, hoàn phí), báo cáo giao dịch.
- Helm/Kubernetes deploy, API Gateway nâng cấp (Kong/Nginx), service discovery.
- Sentry/OpenTelemetry tracing xuyên service theo `payment_id`.
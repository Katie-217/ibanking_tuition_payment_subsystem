# Tài liệu 13 — Kế hoạch triển khai chi tiết (giai đoạn solo)

> **Bối cảnh:** Từ **10/09/2026**, dự án do **Katie toàn quyền phụ trách** (cả TASK-A, TASK-B,
> TASK-C của Sprint 1 cũ). Tài liệu này thay thế mốc thời gian Sprint 1 trong
> [PHAN-CONG-CONG-VIEC.md](PHAN-CONG-CONG-VIEC.md) — *output checklist từng task trong đó vẫn
> dùng làm định nghĩa hoàn thành*, chỉ đổi người làm và lịch.
>
> Mọi quy trình tại [docs/fr/00-quy-trinh-git.md](fr/00-quy-trinh-git.md) **vẫn giữ nguyên**:
> mỗi chức năng 1 nhánh → commit chuẩn → push → PR → merge → dọn nhánh → cập nhật nhật ký.

## 1. Điều chỉnh quy trình cho chế độ 1 người

| Quy tắc cũ | Điều chỉnh | Lý do |
|---|---|---|
| R5: chờ thành viên khác duyệt PR, không tự merge | Mở PR kèm **checklist tự review** (bên dưới) rồi tự merge | Không còn thành viên thứ hai |
| Reviewer kiểm FR/mã lỗi/test | Tự kiểm bằng checklist dưới đây trước khi bấm merge | Thay thế review chéo |

**Checklist tự review trước khi merge mọi PR (bắt buộc):**

1. `python scripts/check_env.py` → toàn ✅.
2. `python scripts/test_api.py` (hoặc test riêng của service) → PASS không tệ hơn trước.
3. Endpoint/mã lỗi/status khớp [docs/03](03-thiet-ke-rest-api.md) + [docs/10](10-quy-dinh-ma-phan-hoi.md) — không tự đặt mã mới.
4. Không sửa file ngoài vùng cho phép; file dùng chung (schema, `endpoints.js`, `shared/**`) chỉ sửa khi đã ghi rõ trong PR.
5. Đã cập nhật `docs/NHAT-KY-CONG-VIEC.md`: mục 2 (trạng thái) + mục 3 (nếu ảnh hưởng máy khác) + mục 4 (entry).

## 2. Hiện trạng đầu kỳ (10/09/2026)

| Hạng mục | Trạng thái |
|---|---|
| Tài liệu 01–12 + FR-01→08 + quy trình git | ✅ xong, đã push GitHub |
| DB 6 database (schema + seed + bcrypt) | ✅ xong |
| auth `:8001` · payer `:8002` · tuition `:8003` | ✅ xong, 18/18 test PASS |
| `frontend/js/endpoints.js` + `api-client.js` | ✅ xong |
| **api-gateway `:8000`** | ⬜ còn |
| **payment-service `:8004`** (FR-03→08) | ⬜ còn |
| **otp-service `:8005`** | ⬜ còn |
| **notification-service `:8006`** (Gmail SMTP) | ⬜ còn |
| **Frontend 4 màn hình** | ⬜ còn |
| **Test concurrency 2 case** | ⬜ còn |
| Docker Compose | ⬜ tùy chọn, làm cuối |

## 3. Kế hoạch theo ngày (10/09 → 17/09/2026)

> Làm xong sớm ngày nào thì dồn lên ngày sau. Mỗi khối = 1 nhánh + 1 PR.
> "Output" là điều kiện để tick hoàn thành khối đó.

### Ngày 1 — Thứ 5, 10/09: Baseline + api-gateway

| Việc | Nhánh | Output cần đạt |
|---|---|---|
| Push toàn bộ tài liệu + code nền tảng lên GitHub | (main, baseline) | ✅ Đã xong — 6 commit + PR #1 (fix Windows-auth DSN) |
| Tài liệu kế hoạch này + cập nhật nhật ký | `docs/ke-hoach-trien-khai-solo` | File này merge; NHAT-KY mục 2/3/4 cập nhật |
| api-gateway `:8000` | `feat/api-gateway` | Gateway route auth/payer/tuition; JWT kiểm tra tại gateway; CORS; `GET /health` tổng hợp; test_api 18/18 PASS **qua `:8000`** |

### Ngày 2 — Thứ 6, 11/09: otp-service

| Việc | Nhánh | Output cần đạt |
|---|---|---|
| otp-service `:8005` + `scripts/test_otp.py` | `feat/otp-service` | generate (ACTIVE cũ → REPLACED rồi sinh mới) · verify đúng → USED · sai 1–4 lần → attempts tăng, còn ACTIVE · sai lần 5 → LOCKED · hết hạn → EXPIRED · invalidate → CANCELLED (idempotent) · thiếu `X-Internal-Token` → 403. `test_otp.py` PASS toàn bộ |

### Ngày 3 — Thứ 7, 12/09: notification-service

| Việc | Nhánh | Output cần đạt |
|---|---|---|
| notification-service `:8006` + `scripts/test_notification.py` | `feat/notification-gmail-smtp` | Email OTP + email xác nhận (CC `finance_email` nhà trường) gửi **thật** qua Gmail App Password; ghi `email_outbox`; SMTP lỗi → ghi FAILED + trả 503 `SERVICE_UNAVAILABLE`; `.env.example` thêm `GMAIL_USER`, `GMAIL_APP_PASSWORD`, `MAIL_FROM_NAME`; NHAT-KY mục 3 ghi rõ |

### Ngày 4 — CN, 13/09: payment-service lõi (FR-03 + FR-04)

| Việc | Nhánh | Output cần đạt |
|---|---|---|
| POST /payments (tạo GD + khóa tuition + gửi OTP) và POST /payments/{id}/verify-otp (verify → PROCESSING → capture → PAID → SUCCESS → email) | `feat/fr03-fr04-payment-core` | Luồng end-to-end qua `:8000`: login → tạo GD nhận OTP (mock đọc code từ DB khi test) → verify → số dư trừ đúng, tuition PAID, history lưu, email xác nhận gửi. Saga bù trừ: capture lỗi → payment FAILED + release tuition |

### Ngày 5 — Thứ 2, 14/09: payment-service phần còn lại (FR-05→08) + file dùng chung

| Việc | Nhánh | Output cần đạt |
|---|---|---|
| resend-otp (rate limit 30s) · cancel · GET /payments + /payments/{id} · job quét hết hạn 5–10s (tự EXPIRED + hoàn tiền nếu đã capture + release tuition) | `feat/fr05-fr08-payment-extras` | 4 endpoint + job chạy đúng FSM; GD quá hạn tự EXPIRED |
| Cập nhật `scripts/run_dev.bat` (bật đủ 7 service) · `scripts/test_api.py` (mở rộng luồng thanh toán) · `frontend/js/endpoints.js` (bổ sung payment/otp/history) | cùng nhánh | `run_dev.bat` khởi động đủ; `test_api.py` PASS toàn bộ gồm luồng mới |

### Ngày 6 — Thứ 3, 15/09: Frontend 4 màn hình

| Việc | Nhánh | Output cần đạt |
|---|---|---|
| `index.html` + `dashboard.html` (dữ liệu thật) | `feat/frontend-login-dashboard` | Login validate client + lỗi theo `e.code`; dashboard load 3 API song song; badge đúng màu docs/10; logout; guard token |
| `payment.html` + `history.html` | `feat/frontend-otp-history` | Modal xác nhận → màn OTP (đếm ngược 5:00, auto-submit, gửi lại sau 30s, hủy GD) → màn kết quả; history lọc + phân trang + chi tiết; không có `fetch(`/URL tay — mọi request qua `API_ENDPOINTS` + `ApiClient` |

### Ngày 7 — Thứ 4, 16/09: Test concurrency 2 case

| Việc | Nhánh | Output cần đạt |
|---|---|---|
| Case 1: 1 tài khoản, 2 GD đồng thời (dư 1tr, GD 700k + 500k) → chỉ 1 thành công, dư không âm | `test/concurrency-double-payment` | Script bắn 2 request song song → đúng 1 SUCCESS, 1 FAILED `INSUFFICIENT_BALANCE`/`STATE_CONFLICT`; balance ≥ 0 |
| Case 2: 2 tài khoản cùng thanh toán 1 khoản học phí | cùng nhánh | Chỉ 1 SUCCESS (khóa `ux_payments_success` + `UNPAID→PAYING` conditional update); GD thua → FAILED `PAYMENT_CONFLICT_CONCURRENT` + được hoàn tiền/hoàn khóa đúng |

### Ngày 8 — Thứ 5, 17/09: Hoàn thiện & demo

| Việc | Nhánh | Output cần đạt |
|---|---|---|
| `docker-compose.yml` (tùy chọn) · README chạy thử đầy đủ · kịch bản demo + screenshot · review checklist `PHAN-CONG-CONG-VIEC.md` toàn bộ | `chore/final-polish` | Repo clone về là chạy được theo README; toàn bộ output checklist được tick; NHAT-KY khép lại |

## 4. Rủi ro & xử lý

| Rủi ro | Phương án |
|---|---|
| Gmail App Password chưa có | Tạo ngay ngày 2 (đi trước lịch 1 ngày); nếu treo → test notification bằng mock SMTP log, đánh dấu TODO, không chặn payment-service |
| SQL Server Express khác máy demo | README ghi rõ cả 2 cách cấu hình: `sa` password hoặc Windows Auth (`DB_UID=` rỗng) |
| Trễ lịch | Thứ tự ưu tiên: payment-service (trái tim đồ án) > gateway > otp/notification > frontend > concurrency test > docker. Docker bị cắt đầu tiên nếu thiếu thời gian |

# Nhật ký công việc & Phân công (WORK LOG)

> **File này là nơi giao việc + báo cáo tiến độ của cả nhóm.** Nhóm trưởng giao việc và deadline
> ở mục 2; thành viên **cập nhật trạng thái khi bắt đầu làm** và **ghi nhật ký khi làm xong**.
>
> 🔎 **Thứ tự đọc khi ngồi vào làm:** file này (biết ai đã làm gì, cần cài gì) →
> [docs/PHAN-CONG-CONG-VIEC.md](PHAN-CONG-CONG-VIEC.md) (task của mình, output phải tick, vùng file
> được sửa) → làm → tick output + ghi entry ở mục 4 dưới đây.
>
> Bắt buộc theo quy trình tại [docs/fr/00-quy-trinh-git.md](fr/00-quy-trinh-git.md) mục 8.

---

## 1. Quy tắc cập nhật (bắt buộc, không được bỏ)

| Thời điểm | Phải cập nhật gì |
|---|---|
| Nhận việc | Nhóm trưởng điền **Người làm + Deadline** vào bảng mục 2 |
| **Khi bắt đầu làm** | Tự đổi trạng thái sang 🔄 **Đang làm**, ghi **ngày bắt đầu** + **tên nhánh** |
| **Khi làm xong** (trước khi mở PR) | Đổi trạng thái 🧪 **Chờ review**, thêm 1 **entry đầy đủ** ở mục 4 |
| Sau khi PR được merge | Đổi trạng thái ✅ **Đã xong**, điền số PR |
| Khi bị vướng | Đổi ⛔ **Bị chặn** + ghi rõ vướng ở đâu, cần ai giúp |

**Ký hiệu trạng thái:** ⬜ Chưa bắt đầu · 🔄 Đang làm · 🧪 Chờ review (đã mở PR) · ✅ Đã xong (đã merge) · ⛔ Bị chặn

**Commit nhật ký** đi kèm PR của chính chức năng đó: `docs(log): update work log for FR-03`.

---

## 2. Bảng phân công & deadline

> Nhóm trưởng điền cột *Người làm* + *Deadline*. Thành viên điền *Bắt đầu*, *Nhánh*, *Trạng thái*, *PR*.
>
> Chi tiết từng task (mô tả, output phải tick, vùng file được/không được sửa):
> **[docs/PHAN-CONG-CONG-VIEC.md](PHAN-CONG-CONG-VIEC.md)**.

| Mã | Chức năng / công việc | Người làm | Deadline | Bắt đầu | Nhánh | Trạng thái | PR |
|---|---|---|---|---|---|---|---|
| — | Bộ tài liệu 01→12 + docs/fr + thiết lập Git | **Katie** | 04/09 | 25/08 | (trước khi có repo) | ✅ | — |
| — | shared lib + auth/payer/tuition service + bộ test 18 case | **Katie** | 31/08 | 28/08 | (trước khi có repo) | ✅ | — |
| — | Baseline push GitHub + fix Windows-auth DSN | **Katie** | 10/09 | 10/09 | `fix/shared-windows-auth-dsn` | ✅ | #1 |
| — | Kế hoạch triển khai solo docs/13 | **Katie** | 10/09 | 10/09 | `docs/ke-hoach-trien-khai-solo` | 🔄 | |
| TASK-A | otp-service `:8005` (FR-03/04/05) | **Katie** *(tiếp quản 10/09)* | 11/09 | 11/09 | `feat/otp-service` | ⬜ | |
| TASK-A | notification-service `:8006` — Gmail SMTP (BR-14) | **Katie** *(tiếp quản 10/09)* | 12/09 | 12/09 | `feat/notification-gmail-smtp` | ⬜ | |
| TASK-B | Frontend: đăng nhập + trang chính (FR-01, FR-02) | **Katie** *(tiếp quản 10/09)* | 15/09 | 15/09 | `feat/frontend-login-dashboard` | ⬜ | |
| TASK-B | Frontend: màn OTP + lịch sử (FR-03→FR-07) | **Katie** *(tiếp quản 10/09)* | 15/09 | 15/09 | `feat/frontend-otp-history` | ⬜ | |
| TASK-C | api-gateway `:8000` | **Katie** | 10/09 | 10/09 | `feat/api-gateway` | 🧪 | #4 |
| TASK-C | payment-service `:8004` — orchestrator + FSM + job quét (FR-03→FR-08) | **Katie** | 13–14/09 | 13/09 | `feat/fr03-fr04-payment-core` → `feat/fr05-fr08-payment-extras` | ⬜ | |
| HT-03 | Test đồng thời (2 case concurrency) | **Katie** | 16/09 | 16/09 | `test/concurrency-double-payment` | ⬜ | |

> **⚡ Thay đổi tổ chức 10/09/2026:** Katie tiếp quản toàn bộ TASK-A + TASK-B (nguồn A, B không
> tham gia tiếp). Lịch và quy trình mới xem **[docs/13-ke-hoach-trien-khai.md](13-ke-hoach-trien-khai.md)**.

---

## 3. Việc phải làm sau khi pull code mới về

> Ai thay đổi thứ ảnh hưởng đến máy người khác (thêm thư viện, thêm biến `.env`, đổi schema DB,
> thêm service/port) thì **bắt buộc** thêm 1 dòng vào đây — để 2 người kia pull về là chạy được ngay,
> không mất thời gian dò lỗi.

| Ngày | Người | Thay đổi ảnh hưởng người khác | Việc bạn phải làm sau khi pull |
|---|---|---|---|
| 2026-08-31 | Katie | Thêm `services/requirements.txt`, `services/.env.example`, 3 service nền tảng | `pip install -r services/requirements.txt` → copy `.env.example` thành `services/.env`, điền `DB_PWD` → chạy `db/01→03` trên SSMS → `python db/generate_password_hashes.py` rồi dán UPDATE vào SSMS |
| 2026-09-04 | Katie | Thêm `.gitignore`, `.gitattributes` | Không cần làm gì (chỉ ảnh hưởng cách git theo dõi file) |
| 2026-09-04 | Katie | Thêm `docs/PHAN-CONG-CONG-VIEC.md` (bảng phân công Sprint 1) | Đọc task của mình trong đó trước khi code |
| 2026-09-10 | Katie | PR #1 sửa `db_dsn()` trong `services/shared/config.py`: nhánh Windows Auth thêm `TrustServerCertificate=yes` | Ai dùng Windows Authentication chỉ cần đặt `DB_UID=` (rỗng) trong `services/.env` — kết nối được với SQL Server Express local (chứng chỉ tự ký). Ai đang dùng `sa` + mật khẩu thì không bị ảnh hưởng |
| 2026-09-10 | Katie | PR #3 sửa `db/02-schema.sql` (migration + index BR-07) | **Chạy lại `db/02-schema.sql` trên SSMS/sqlcmd** — DB cũ sẽ được thêm cột `otps.uid/status/...`, `payments.active_uid`, xóa `uq_otps_code`/`uq_otps_payment` cũ, tạo lại `ux_payments_active` đúng chuẩn. Chạy qua sqlcmd thì script đã tự SET QUOTED_IDENTIFIER ON |

---

## 4. Nhật ký chi tiết (entry mới nhất ở trên cùng)

### Mẫu entry — copy nguyên khối này khi ghi nhật ký mới

```markdown
### [YYYY-MM-DD] FR-xx — <tên chức năng> — <tên thành viên>
- **Trạng thái:** 🧪 Chờ review / ✅ Đã xong
- **Nhánh / PR:** `feat/frXX-...` / PR #__
- **Đã làm gì:** liệt kê gạch đầu dòng những gì thực sự chạy được (endpoint nào, màn hình nào)
- **Công nghệ / thuật toán dùng:** thư viện, kỹ thuật (vd: conditional UPDATE chống dư âm,
  filtered unique index chống double-pay, saga bù trừ, FSM trạng thái, bcrypt, JWT HS256)
- **Liên kết bên thứ 3:** dịch vụ ngoài + cần khóa/bí mật gì (vd: Gmail SMTP cần App Password 16 ký tự)
- **Để người khác pull về chạy được:**
  - Thư viện mới cần cài: ...
  - Biến `.env` mới cần thêm: ...
  - Script DB phải chạy lại: ...
  - Service/port cần bật: ...
  - Lệnh chạy + lệnh test: ...
- **Cách kiểm tra nhanh:** vài bước để reviewer tự xác nhận chức năng chạy đúng
- **Còn nợ / lưu ý:** phần chưa làm, chỗ dễ vỡ, TODO cho PR sau
```

---

### [2026-09-10] api-gateway :8000 — Katie
- **Trạng thái:** 🧪 Chờ review (PR #4)
- **Nhánh / PR:** `feat/api-gateway` / PR #4
- **Đã làm gì:**
  - `services/api-gateway/main.py` — cổng vào duy nhất: route theo tiền tố đường dẫn
    (`/auth/*` → 8001, `/payers/*` → 8002, `/tuition|/tuitions/*` → 8003, `/payments/*` → 8004),
    kiểm JWT ngay tại gateway (decode HS256 chung `JWT_SECRET`), CORS cho web local.
  - `GET /health` tổng hợp trạng thái 6 service (concurrent qua httpx).
  - Chặn tuyệt đối `/internal/*` qua gateway (404) — endpoint nội bộ chỉ gọi trực tiếp giữa
    service kèm `X-Internal-Token`.
  - Service không phản hồi → 503 `SERVICE_UNAVAILABLE` envelope chuẩn.
- **Công nghệ / thuật toán dùng:** FastAPI catch-all proxy + httpx.AsyncClient; reverse proxy
  whitelist header (Authorization, Idempotency-Key, Content-Type); `allow_origin_regex` CORS.
- **Liên kết bên thứ 3:** không.
- **Để người khác pull về chạy được:**
  - Service/port cần bật: thêm gateway `python -m uvicorn main:app --port 8000 --app-dir services/api-gateway`
    (PYTHONPATH trỏ `services/`).
  - Biến `.env` tùy chọn (mặc định localhost): `AUTH_SERVICE_URL`, `PAYER_SERVICE_URL`,
    `TUITION_SERVICE_URL`, `PAYMENT_SERVICE_URL`, `OTP_SERVICE_URL`, `NOTIFICATION_SERVICE_URL`.
  - Frontend không đổi gì — `endpoints.js` đã trỏ sẵn `:8000`.
- **Cách kiểm tra nhanh:** login qua `:8000` rồi gọi `/auth/me`, `/payers/me`, `/tuition/me`;
  không token → 401; `/internal/...` → 404; `GET /health` liệt kê trạng thái từng service.
- **Còn nợ / lưu ý:** `run_dev.bat` chưa bật gateway (cập nhật ở PR payment-service); 3 service
  chưa code hiện báo `down` trong `/health` — đúng thực trạng.


- **Trạng thái:** 🧪 Chờ review (PR #3)
- **Nhánh / PR:** `db/fix-migration-batches` / PR #3
- **Đã làm gì:**
  - Tách khối migration OTPDB + payments thành từng câu 1 batch (GO): trước đây SQL Server
    compile cả batch trước khi chạy → Msg 207 → **khối migration không bao giờ chạy trên DB
    cũ** (thiếu cột `otps.uid/status/...`, còn sót `uq_otps_code`/`uq_otps_payment` chặn gửi
    lại OTP).
  - Tạo lại `ux_payments_active` (BR-07) theo `(uid) WHERE status IN (PENDING, OTP_SENT,
    PROCESSING)`: bản lọc theo computed column `active_uid` bị SQL Server từ chối (Msg 10609)
    → index chưa từng được tạo.
  - Thêm `SET QUOTED_IDENTIFIER ON` đầu script để chạy được qua sqlcmd.
- **Công nghệ / thuật toán dùng:** filtered unique index, batch compilation của SQL Server.
- **Liên kết bên thứ 3:** không.
- **Để người khác pull về chạy được:** **chạy lại `db/02-schema.sql`** (idempotent) rồi
  `python scripts/test_api.py` → 28/28 PASS.
- **Cách kiểm tra nhanh:** thử INSERT 2 payment active cùng uid → SQL Server chặn duplicate
  key `ux_payments_active`.
- **Còn nợ / lưu ý:** không đổi bảng mới, chỉ sửa migration — dữ liệu seed không mất.

### [2026-09-10] Bàn giao toàn quyền + baseline push GitHub + fix DSN — Katie
- **Trạng thái:** ✅ Đã xong (PR #1) · kế hoạch solo 🔄
- **Nhánh / PR:** `fix/shared-windows-auth-dsn` / PR #1 (đã merge)
- **Đã làm gì:**
  - Tiếp quản toàn bộ TASK-A + TASK-B (nguồn A, B không tham gia tiếp) — lịch mới trong
    `docs/13-ke-hoach-trien-khai.md`.
  - Push baseline 6 commit lên `main` GitHub (tài liệu + db + 3 service nền tảng + test + endpoint layer).
  - Fix `db_dsn()` Windows Auth: thêm `Encrypt=yes;TrustServerCertificate=yes` — trước đó ODBC
    Driver 18 từ chối chứng chỉ tự ký của SQL Server Express (lỗi SSL 08001).
  - Khôi phục môi trường máy local: cài đủ thư viện, tạo `services/.env` dùng Windows Auth
    (`DB_UID=` rỗng, `DB_SERVER=localhost\SQLEXPRESS`), `check_env.py` toàn ✅.
- **Công nghệ / thuật toán dùng:** không có thuật toán mới (chỉ fix chuỗi kết nối ODBC).
- **Liên kết bên thứ 3:** GitHub repo `Katie-217/ibanking_tuition_payment_subsystem`.
- **Để người khác pull về chạy được:**
  - Không cần cài thêm gì mới; ai dùng Windows Auth đặt `DB_UID=` rỗng trong `services/.env`.
  - Lệnh kiểm tra: `python scripts/check_env.py` → toàn ✅.
- **Cách kiểm tra nhanh:** `git log --oneline` thấy 6 commit baseline; `check_env.py` kết nối
  được cả 6 database.
- **Còn nợ / lưu ý:** từ nay PR tự review theo checklist trong `docs/13` mục 1 (không còn
  thành viên thứ hai duyệt); Gmail App Password cần tạo trước ngày làm notification-service.

### [2026-09-04] Tài liệu FR + chuẩn API/mã lỗi + thiết lập Git — Katie
- **Trạng thái:** ✅ Đã xong
- **Nhánh / PR:** làm trực tiếp trước khi có repo (chưa qua PR)
- **Đã làm gì:**
  - `docs/fr/` — mỗi chức năng 1 file: `FR-01` … `FR-08` (mô tả, flow, API dùng, UI cần build,
    logic backend, ràng buộc BR, output mong đợi, bảng mã response, nhánh git).
  - `docs/09` cách biểu diễn API trên frontend qua lớp endpoint; `docs/10` quy định mã phản hồi
    + trạng thái nghiệp vụ; `docs/11` khái niệm endpoint/resource + danh mục toàn bộ API;
    `docs/12` thư viện cần cài.
  - `docs/fr/00-quy-trinh-git.md` — quy ước nhánh/commit/PR cho nhóm 3 người.
  - Khởi tạo git local (`main`), thêm `.gitignore` + `.gitattributes`, nối remote `origin`.
- **Công nghệ / thuật toán dùng:** không có code mới (chỉ tài liệu + cấu hình git).
- **Liên kết bên thứ 3:** GitHub (repo nhóm, link trong group chat).
- **Để người khác pull về chạy được:** không cần cài gì thêm; đọc `docs/fr/00-quy-trinh-git.md`
  trước khi bắt đầu chức năng đầu tiên.
- **Cách kiểm tra nhanh:** mở `docs/11-tai-lieu-api-endpoint-resource.md` — bảng danh mục API phải
  khớp với `frontend/js/endpoints.js`.
- **Còn nợ / lưu ý:** chưa commit + chưa push lần đầu lên `main`; mapping khoa/ngành/hệ theo MSSV
  vẫn là dữ liệu DEMO, chờ quy tắc giải mã MSSV thật của TDTU.

### [2026-08-31] Nền tảng backend + bộ test API — Katie
- **Trạng thái:** ✅ Đã xong
- **Nhánh / PR:** làm trực tiếp trước khi có repo (chưa qua PR)
- **Đã làm gì:**
  - `services/shared/` — `config.py` (đọc `.env`), `db.py` (context manager commit/rollback),
    `errors.py` (envelope lỗi thống nhất), `security.py` (JWT + token nội bộ).
  - auth-service `:8001` — `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`, `GET /health`.
  - payer-service `:8002` — `GET /payers/me`, `POST /internal/balance/capture`,
    `POST /internal/balance/release`, `GET /health`.
  - tuition-service `:8003` — `GET /tuition/me`, `GET /internal/tuitions/{id}`,
    `.../lock`, `.../paid`, `.../release`, `GET /health`.
  - `scripts/check_env.py`, `scripts/run_dev.bat`, `scripts/test_api.py` (18 test case),
    `docs/08-huong-dan-test-api.md`.
- **Công nghệ / thuật toán dùng:** FastAPI + Uvicorn; pyodbc (transaction commit/rollback);
  JWT HS256 (`PyJWT`); bcrypt cost 12; **conditional UPDATE `WHERE available_balance >= amount`**
  chống dư âm; **idempotency theo `payment_id`** qua `UNIQUE(payment_id, change_type)` trên
  `balance_ledger`; **conditional UPDATE `UNPAID→PAYING`** chống thanh toán 2 lần; `hmac.compare_digest`
  so sánh token nội bộ.
- **Liên kết bên thứ 3:** SQL Server qua **ODBC Driver 18** (bắt buộc cài trên máy mỗi người).
- **Để người khác pull về chạy được:**
  - Thư viện: `pip install -r services/requirements.txt` (fastapi, uvicorn, pyodbc, PyJWT, bcrypt, httpx, python-dotenv).
  - Biến `.env`: copy `services/.env.example` → `services/.env`, điền `DB_PWD`, `JWT_SECRET`, `INTERNAL_TOKEN`.
  - Script DB: chạy `db/01-create-databases.sql` → `db/02-schema.sql` → `db/03-seed.sql` trên SSMS.
  - Mật khẩu demo: `python db/generate_password_hashes.py` → dán 3 lệnh UPDATE vào SSMS (mật khẩu `abc12345`).
  - Chạy: `scripts/run_dev.bat` (bật 3 service) → test: `python scripts/test_api.py`.
- **Cách kiểm tra nhanh:** `python scripts/check_env.py` toàn ✅ và `python scripts/test_api.py` báo 18/18 PASS.
- **Còn nợ / lưu ý:** chưa có payment-service, otp-service, notification-service, api-gateway;
  bộ test chạy lại được nhiều lần (tự hoàn tiền + mở khóa nên không để lại dữ liệu bẩn).


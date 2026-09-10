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
| TASK-A | otp-service `:8005` (FR-03/04/05) | **A — *(điền tên)*** | 07/09 | 04/09 | `feat/otp-service` | ⬜ | |
| TASK-A | notification-service `:8006` — Gmail SMTP (BR-14) | **A — *(điền tên)*** | 07/09 | 06/09 | `feat/notification-gmail-smtp` | ⬜ | |
| TASK-B | Frontend: đăng nhập + trang chính (FR-01, FR-02) | **B — *(điền tên)*** | 07/09 | 04/09 | `feat/frontend-login-dashboard` | ⬜ | |
| TASK-B | Frontend: màn OTP + lịch sử (FR-03→FR-07) | **B — *(điền tên)*** | 07/09 | 06/09 | `feat/frontend-otp-history` | ⬜ | |
| TASK-C | api-gateway `:8000` | **Katie** | 07/09 | 04/09 | `feat/api-gateway` | 🔄 | |
| TASK-C | payment-service `:8004` — orchestrator + FSM + job quét (FR-03→FR-08) | **Katie** | 07/09 | 05/09 | `feat/fr03-fr08-payment-service` | ⬜ | |
| HT-03 | Test đồng thời (2 case concurrency) | **Katie** | 07/09 | 07/09 | `test/concurrency-double-payment` | ⬜ | |

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


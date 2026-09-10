# Phân công công việc — Sprint 1: 04/09/2026 → 10/09/2026

> **Bảng phân việc chính thức của nhóm.** Mỗi người chỉ làm đúng task mang tên mình, chỉ sửa
> đúng vùng file được giao, làm xong thì **tick vào ô output** ở đây và **ghi nhật ký**.
>

---

## 0. Quy trình bắt buộc mỗi khi ngồi vào làm (4 bước)

| Bước | Việc | File |
|---|---|---|
| 1 | **Quét nhật ký** để biết người khác đã làm gì, có phải cài thêm thư viện / biến `.env` / chạy lại script DB không | [docs/NHAT-KY-CONG-VIEC.md](NHAT-KY-CONG-VIEC.md) |
| 2 | **Quét file phân công này** → tìm task mang tên mình, đọc mô tả + output + ranh giới file | file này |
| 3 | **Đọc tài liệu** ghi trong mục "Đọc trước khi code" của task | `docs/…` |
| 4 | Làm xong: **tick ✅ output** trong file này + **ghi entry nhật ký** + mở PR | 2 file trên |

Quy trình git (tạo nhánh, pull main, giải conflict, mở PR chờ duyệt): [docs/fr/00-quy-trinh-git.md](fr/00-quy-trinh-git.md).

### Prompt dán cho AI (Copilot / Claude / Cursor) để nắm việc trong 1 lần

```text
Đọc 2 file: docs/NHAT-KY-CONG-VIEC.md (biết trạng thái dự án + môi trường cần cài)
và docs/PHAN-CONG-CONG-VIEC.md (tìm task của tôi: <TÊN TÔI>).
Sau đó đọc các tài liệu mà task đó yêu cầu ở mục "Đọc trước khi code".
Rồi thực hiện đúng phạm vi task: CHỈ tạo/sửa các file trong danh sách "Được tạo / sửa",
TUYỆT ĐỐI không sửa file trong danh sách "KHÔNG được sửa".
Giữ đúng hợp đồng API (docs/03, docs/11) và bảng mã lỗi (docs/10) — không tự đổi tên endpoint,
không tự đặt mã lỗi mới, không đổi schema database.
Làm xong thì tick output trong docs/PHAN-CONG-CONG-VIEC.md và thêm entry vào
docs/NHAT-KY-CONG-VIEC.md theo mẫu có sẵn.
```

---

## 1. Tổng quan sprint

| Task | Người làm | Nội dung | Bắt đầu | Deadline | Nhánh | Trạng thái |
|---|---|---|---|---|---|---|
| **TASK-A** | A — *(điền tên)* | otp-service `:8005` + notification-service `:8006` (Gmail SMTP) | 07/09 | 10/09 | `feat/otp-service` → `feat/notification-gmail-smtp` | ⬜ |
| **TASK-B** | B — *(điền tên)* | Frontend 4 màn hình (login · dashboard · OTP · lịch sử) | 07/09 | 10/09 | `feat/frontend-login-dashboard` → `feat/frontend-otp-history` | ⬜ |
| **TASK-C** | Katie | api-gateway `:8000` + payment-service `:8004` (orchestrator + FSM + job quét) | 04/09 | 07/09 | `feat/api-gateway` → `feat/fr03-fr08-payment-service` | 🔄 |

---

## 2. TASK-A — otp-service (:8005) + notification-service (:8006)

| Mục | Nội dung |
|---|---|
| Người làm | **A — *(điền tên)*** |
| Bắt đầu → Deadline | **07/09/2026 → 10/09/2026 (23:59)** |
| Nhánh | Phần 1: `feat/otp-service` · Phần 2: `feat/notification-gmail-smtp` (2 PR riêng) |
| Trạng thái | ⬜ Chưa bắt đầu |

### 2.1 Mô tả tổng quan

Viết 2 microservice **nội bộ** (chỉ service khác gọi, người dùng không gọi trực tiếp):

- **otp-service `:8005`** quản lý mã OTP 6 số cho từng tài khoản và giao dịch. Bảng OTP giữ lại
  bản ghi trong suốt vòng đời; `status` mô tả `ACTIVE`, `EXPIRED`, `USED`, `LOCKED`,
  `CANCELLED` hoặc `REPLACED`. Tác vụ dọn dữ liệu riêng mới xóa bản ghi terminal.
- **notification-service `:8006`** gửi email thật qua **Gmail SMTP** (App Password): email chứa
  mã OTP, và email xác nhận thanh toán thành công gửi cho sinh viên + copy cho nhà trường.

Cả 2 service đều dùng lại thư viện chung `services/shared/` (config, db, errors, security) —
**đọc và dùng, không sửa**. Xem `services/payer-service/main.py` làm mẫu chuẩn về cách viết
endpoint nội bộ, cách raise lỗi, cách mở connection.

### 2.2 Đọc trước khi code (theo thứ tự)

1. [docs/NHAT-KY-CONG-VIEC.md](NHAT-KY-CONG-VIEC.md) — môi trường cần cài trước.
2. [docs/03-thiet-ke-rest-api.md](03-thiet-ke-rest-api.md) mục **3.3** (otp) và **3.4** (notification) — hợp đồng input/output.
3. [docs/10-quy-dinh-ma-phan-hoi.md](10-quy-dinh-ma-phan-hoi.md) — bảng mã lỗi phải trả đúng.
4. [docs/fr/FR-04-xac-thuc-otp.md](fr/FR-04-xac-thuc-otp.md) + [FR-05](fr/FR-05-gui-lai-otp.md) — nghiệp vụ OTP (BR-08, BR-09).
5. `db/02-schema.sql` phần **E. OTPDB** và **F. NotificationDB** — cấu trúc bảng (chỉ đọc, không sửa).
6. `services/payer-service/main.py` — mẫu code để bắt chước style.

### 2.3 Output cần đạt — làm xong cái nào tick cái đó

**Phần 1 — otp-service `:8005`** (nhánh `feat/otp-service`, xong trong ngày 04–05/09)

- [ ] `services/otp-service/main.py` chạy được: `GET /health` trả `{"status":"ok"}` + kết nối OTPDB
- [ ] `POST /internal/otp/generate` — chuyển OTP ACTIVE cũ sang `REPLACED` **rồi** sinh mã mới 6 số, hạn 5 phút; mã không trùng OTP ACTIVE khác
- [ ] `POST /internal/otp/verify` — **đúng**: cập nhật `USED` + trả `{"verified": true}`
- [ ] `POST /internal/otp/verify` — **sai**: `attempts + 1`, trả 400 `OTP_INVALID` kèm số lần còn lại
- [ ] `POST /internal/otp/verify` — **sai đủ 5 lần**: cập nhật `LOCKED` + trả 400 `OTP_LOCKED`
- [ ] `POST /internal/otp/verify` — **hết hạn**: cập nhật `EXPIRED` + trả 400 `OTP_EXPIRED`
- [ ] `POST /internal/otp/invalidate` — cập nhật `CANCELLED` theo `payment_id`; không có bản ghi cũng trả OK (idempotent)
- [ ] Cả 3 endpoint `/internal/*` bắt buộc header `X-Internal-Token` (dùng `Depends(require_internal)`), thiếu → 403
- [ ] `scripts/test_otp.py` — file test riêng với các bản ghi/transaction độc lập: verify đúng → `USED`,
      verify sai 1–4 lần vẫn `ACTIVE`, sai lần 5 → `LOCKED`, hết hạn → `EXPIRED`, invalidate → `CANCELLED`
- [ ] Sau mỗi tình huống, kiểm tra `OTPDB.dbo.otps` có đúng `status`, `attempts`, `used_at`/
  `invalidated_at`; chỉ tác vụ dọn dữ liệu mới xóa bản ghi terminal

**Phần 2 — notification-service `:8006`** (nhánh `feat/notification-gmail-smtp`, ngày 06–07/09)

- [ ] `services/notification-service/main.py` chạy được: `GET /health` + kết nối NotificationDB
- [ ] `POST /internal/notifications/otp-email` — gửi **email thật** chứa mã OTP tới email sinh viên, ghi 1 dòng vào bảng `email_outbox`
- [ ] `POST /internal/notifications/confirm-email` — gửi email xác nhận cho sinh viên **+ CC email nhà trường** (`schools.finance_email`), ghi các dòng vào bảng `email_outbox`
- [ ] Gmail lỗi tạm thời → không làm vỡ API: ghi trạng thái `FAILED` vào bảng + trả 503 `SERVICE_UNAVAILABLE`
- [ ] Thêm biến mới vào **`services/.env.example`** (chỉ thêm dòng ở cuối): `GMAIL_USER`, `GMAIL_APP_PASSWORD`, `MAIL_FROM_NAME`
- [ ] **Ghi vào mục 3 của nhật ký**: 2 người kia phải thêm 3 biến này vào `services/.env` của họ mới chạy được
- [ ] `scripts/test_notification.py` — test gửi thử 1 email OTP + 1 email xác nhận tới hộp thư của chính mình

**Chung cả 2 phần**

- [ ] Mã lỗi trả về đúng bảng [docs/10](10-quy-dinh-ma-phan-hoi.md) (không tự đặt mã mới)
- [ ] Tick hết output ở trên trong file này
- [ ] Ghi **2 entry nhật ký** (1 cho mỗi PR) theo mẫu ở [docs/NHAT-KY-CONG-VIEC.md](NHAT-KY-CONG-VIEC.md) mục 4
- [ ] Mở 2 PR, mô tả rõ đã làm gì, gán Katie làm reviewer

### 2.4 Ranh giới file

**Được tạo / sửa:**

| File | Ghi chú |
|---|---|
| `services/otp-service/main.py` | tạo mới — toàn quyền |
| `services/notification-service/main.py` | tạo mới — toàn quyền |
| `scripts/test_otp.py`, `scripts/test_notification.py` | tạo mới — file test riêng của bạn |
| `services/.env.example` | **chỉ THÊM** 3 dòng biến Gmail ở cuối, không sửa dòng có sẵn |
| `services/requirements.txt` | chỉ thêm thư viện nếu bắt buộc (ưu tiên `smtplib` có sẵn trong Python, **không cần** cài gì) |
| `docs/NHAT-KY-CONG-VIEC.md` | thêm entry của mình + dòng ở mục 3 |
| `docs/PHAN-CONG-CONG-VIEC.md` | chỉ tick output của TASK-A |

**KHÔNG được sửa** (sửa là gây conflict cho người khác):

| File / thư mục | Vì sao |
|---|---|
| `services/shared/**` | thư viện chung — cần thêm gì thì nhắn Katie, đừng tự sửa |
| `services/auth-service/**`, `payer-service/**`, `tuition-service/**` | đã xong và đã test, không đụng |
| `services/payment-service/**`, `services/api-gateway/**` | Katie đang làm song song |
| `frontend/**` | B đang làm |
| `db/*.sql` | schema do Katie quản lý; phải giữ `otps.status` và các unique index ACTIVE theo schema hiện hành |
| `scripts/test_api.py`, `scripts/run_dev.bat`, `scripts/check_env.py` | file dùng chung, Katie cập nhật |
| `docs/03`, `docs/10`, `docs/11`, `README.md` | tài liệu hợp đồng — muốn đổi phải nhắn nhóm trước |

### 2.5 Cách tự kiểm tra trước khi mở PR

```bash
# tại thư mục gốc dự án
python scripts/check_env.py                       # môi trường phải OK

# chạy service của bạn (mở terminal riêng cho từng service)
set PYTHONPATH=%CD%\services                      # Windows CMD
python -m uvicorn main:app --port 8005 --app-dir services/otp-service --reload
python -m uvicorn main:app --port 8006 --app-dir services/notification-service --reload

python scripts/test_otp.py                        # test của bạn phải PASS hết
python scripts/test_notification.py               # kiểm tra hộp thư nhận được mail thật
python scripts/test_api.py                        # 18/18 PASS — chứng minh bạn không làm vỡ phần cũ
```

Swagger tự động: <http://localhost:8005/docs> và <http://localhost:8006/docs>.

**Định nghĩa hoàn thành TASK-A:** Katie gọi được `generate → verify → invalidate` từ
payment-service mà không cần sửa gì thêm; email OTP và email xác nhận về tới hộp thư thật;
bảng `otps` giữ đúng status terminal sau khi giao dịch kết thúc; tác vụ dọn dữ liệu mới xóa lịch sử cũ.

---

## 3. TASK-B — Frontend 4 màn hình

| Mục | Nội dung |
|---|---|
| Người làm | **B — *(điền tên)*** |
| Bắt đầu → Deadline | **04/09/2026 → 07/09/2026 (23:59)** |
| Nhánh | Phần 1: `feat/frontend-login-dashboard` · Phần 2: `feat/frontend-otp-history` (2 PR riêng) |
| Trạng thái | ⬜ Chưa bắt đầu |

### 3.1 Mô tả tổng quan

Xây toàn bộ giao diện web của phân hệ: **đăng nhập → trang chính → thanh toán/OTP → lịch sử**.
Dùng HTML + CSS + JavaScript thuần (không framework) để bảo vệ đồ án đơn giản, dễ giải thích.

**Nguyên tắc quan trọng nhất:** mọi request **phải** đi qua 2 lớp có sẵn —
`API_ENDPOINTS` (khai báo đường dẫn) + `ApiClient` (gửi request, gắn token, xử lý lỗi).
Trong file trang **không được xuất hiện** `fetch(`, `axios`, hay URL viết tay. Lý do: đổi đường
dẫn API chỉ sửa 1 chỗ. `ApiClient` đã lo sẵn: gắn `Authorization: Bearer`, đọc envelope lỗi,
tự đăng xuất khi 401.

Trong 4 ngày này **payment-service chưa xong** (Katie đang làm) → màn hình OTP và lịch sử làm
UI đầy đủ nhưng tạm dùng **dữ liệu giả**; đánh dấu rõ `// TODO: bỏ mock khi payment-service xong`
để ghép nối sau. Riêng login + dashboard phải chạy **dữ liệu thật** (3 service đã hoạt động).

### 3.2 Đọc trước khi code (theo thứ tự)

1. [docs/NHAT-KY-CONG-VIEC.md](NHAT-KY-CONG-VIEC.md) — cách bật backend để test giao diện.
2. [docs/09-readme-bieu-dien-api-endpoint-lop.md](09-readme-bieu-dien-api-endpoint-lop.md) — **bắt buộc**: cách dùng `API_ENDPOINTS` + `ApiClient`, có sẵn mẫu code từng luồng.
3. [docs/fr/FR-01-dang-nhap.md](fr/FR-01-dang-nhap.md), [FR-02](fr/FR-02-trang-chu.md), [FR-03](fr/FR-03-tao-giao-dich-gui-otp.md), [FR-04](fr/FR-04-xac-thuc-otp.md), [FR-05](fr/FR-05-gui-lai-otp.md), [FR-06](fr/FR-06-huy-giao-dich.md), [FR-07](fr/FR-07-lich-su-giao-dich.md) — mục **"Frontend — UI cần build"** của từng file mô tả chính xác từng thành phần.
4. [docs/10-quy-dinh-ma-phan-hoi.md](10-quy-dinh-ma-phan-hoi.md) mục **4** (mã lỗi → hiển thị gì) và mục **5** (màu badge trạng thái).
5. `frontend/js/endpoints.js` + `frontend/js/api-client.js` — **đọc kỹ, chỉ dùng, không sửa**.
6. [docs/08-huong-dan-test-api.md](08-huong-dan-test-api.md) — cách bật backend + 3 tài khoản demo để thử UI.

### 3.3 Output cần đạt — làm xong cái nào tick cái đó

**Phần 1 — Đăng nhập + Trang chính** (nhánh `feat/frontend-login-dashboard`, ngày 04–05/09, **dữ liệu thật**)

- [ ] `frontend/index.html` — form MSSV + mật khẩu, nút [Đăng nhập], nạp `api-client.js` rồi `endpoints.js`
- [ ] Validate client: MSSV khớp `^\d{3}[A-Za-z]\d{4}$` (vd `521H0092`), ô trống → báo lỗi ngay, chưa gọi API
- [ ] Đăng nhập đúng → lưu token bằng `ApiClient.setToken()` → chuyển `dashboard.html`
- [ ] Hiển thị lỗi theo `e.code`: `AUTH_INVALID_CREDENTIALS` / `VALIDATION_ERROR` / `FORBIDDEN` (tài khoản bị khóa) / `SERVICE_UNAVAILABLE`
- [ ] Nút đang gửi → disable + chữ "Đang đăng nhập…" (chống double-click)
- [ ] `frontend/dashboard.html` — gọi **song song** `auth.me` + `payers.me` + `tuition.me` bằng `Promise.all`
- [ ] Card hồ sơ sinh viên: MSSV, khóa, **Trường / Khoa (mã) / Ngành (mã) / Hệ (mã hệ)**
- [ ] Card số dư: format tiền Việt `Intl.NumberFormat("vi-VN")` → `15.000.000 ₫`
- [ ] Bảng học phí: Kỳ học · Số tiền · Hạn nộp · Badge trạng thái · nút [Thanh toán] **chỉ hiện với `UNPAID`**
- [ ] Badge màu đúng [docs/10](10-quy-dinh-ma-phan-hoi.md) mục 5.2: `UNPAID` đỏ · `PAYING` cam · `PAID` xanh lá
- [ ] Nút [Đăng xuất] → gọi `auth.logout` → `ApiClient.clearToken()` → về `index.html`
- [ ] Mở `dashboard.html` khi chưa có token → tự chuyển về `index.html`
- [ ] Trạng thái đang tải (skeleton/spinner) + nút "Thử lại" khi API lỗi

**Phần 2 — Màn hình OTP + Lịch sử** (nhánh `feat/frontend-otp-history`, ngày 06–07/09, **cho phép mock**)

- [ ] Modal xác nhận thanh toán: kỳ học, số tiền, số dư hiện tại, nút [Hủy] + [Xác nhận & nhận OTP]
- [ ] Màn hình nhập OTP: ô 6 chữ số (auto nhảy focus), **đồng hồ đếm ngược 5:00**, tự submit khi đủ 6 số
- [ ] Nút [Gửi lại mã] — **ẩn trong 30 giây đầu**, sau đó mới hiện (tránh dính 429 `RATE_LIMITED`)
- [ ] Nút [Hủy giao dịch] + dialog xác nhận "số dư sẽ được hoàn lại"
- [ ] Xử lý lỗi OTP theo code: `OTP_INVALID` (còn N lần) · `OTP_EXPIRED` (ẩn ô nhập, bật gửi lại) · `OTP_LOCKED` (thông báo đã hủy + hoàn tiền) · `STATE_CONFLICT`
- [ ] Màn hình kết quả thành công: ✓, mã giao dịch, số tiền, thời gian, nút [Về trang chính]
- [ ] `frontend/history.html` — bảng lịch sử: Ngày giờ · Kỳ học · Số tiền · Badge trạng thái · Mã GD
- [ ] Chip lọc trạng thái + phân trang (đọc `page`/`size`/`total` từ response) + modal chi tiết 1 giao dịch
- [ ] Badge 7 trạng thái payment đúng màu [docs/10](10-quy-dinh-ma-phan-hoi.md) mục 5.1
- [ ] Trạng thái rỗng: "Chưa có giao dịch nào"
- [ ] Mọi chỗ mock đều có `// TODO: bỏ mock khi payment-service xong` + liệt kê trong entry nhật ký

**Chung cả 2 phần**

- [ ] Không có `fetch(` / URL viết tay trong bất kỳ file trang nào — tất cả qua `API_ENDPOINTS` + `ApiClient`
- [ ] `frontend/css/style.css` dùng chung cho 4 trang (một bộ màu, một bộ badge)
- [ ] Giao diện dùng được trên màn hình hẹp (responsive cơ bản), chữ tiếng Việt không lỗi font (`<meta charset="utf-8">`)
- [ ] Tick hết output ở trên + ghi **2 entry nhật ký** + mở 2 PR, gán Katie làm reviewer

### 3.4 Ranh giới file

**Được tạo / sửa:**

| File | Ghi chú |
|---|---|
| `frontend/index.html`, `dashboard.html`, `payment.html`, `history.html` | tạo mới — toàn quyền |
| `frontend/css/**` | tạo mới — toàn quyền |
| `frontend/js/pages/**` | tạo mới: `login.js`, `dashboard.js`, `payment.js`, `history.js` — logic từng trang |
| `frontend/assets/**` | ảnh, logo (nếu cần) |
| `docs/NHAT-KY-CONG-VIEC.md` | thêm entry của mình |
| `docs/PHAN-CONG-CONG-VIEC.md` | chỉ tick output của TASK-B |

**KHÔNG được sửa:**

| File / thư mục | Vì sao |
|---|---|
| `frontend/js/endpoints.js` | **lớp endpoint dùng chung** — thiếu đường dẫn nào thì nhắn Katie thêm, tuyệt đối không tự sửa |
| `frontend/js/api-client.js` | lớp gọi API dùng chung — chỉ đọc và dùng |
| `services/**` | toàn bộ backend là việc của A và Katie |
| `db/**`, `scripts/**` | không liên quan tới giao diện |
| `docs/03`, `docs/09`, `docs/10`, `docs/11`, `README.md` | tài liệu hợp đồng — muốn đổi phải nhắn nhóm trước |

### 3.5 Cách tự kiểm tra trước khi mở PR

```bash
# 1) Bật backend để có dữ liệu thật (terminal riêng, tại thư mục gốc dự án)
scripts\run_dev.bat            # auth :8001, payer :8002, tuition :8003

# 2) Mở frontend bằng web server tĩnh (KHÔNG mở trực tiếp file:// vì sẽ bị CORS)
python -m http.server 5500 --directory frontend
#    rồi vào: http://localhost:5500/index.html
```

Trong 4 ngày này api-gateway `:8000` chưa chắc xong → nếu login lỗi *không kết nối được*, tạm khai
báo base URL trỏ thẳng service trong trang đang test (đặt **trước** thẻ nạp `endpoints.js`):

```html
<script>window.API_BASE_URL = "http://localhost:8001";</script>  <!-- tạm, chỉ để test login -->
```

⚠️ **Không commit** dòng tạm này — khi Katie xong gateway thì mọi thứ về đúng `:8000`.

Tài khoản demo (mật khẩu `abc12345`): `521H0092` (dư 15tr, nợ 7tr) · `522H0145` (dư 2tr, nợ 1,5tr) ·
`523H0201` (dư 1tr, nợ 5tr + 1 khoản đã nộp — dùng để thử badge `PAID` và lỗi thiếu dư).

**Định nghĩa hoàn thành TASK-B:** đăng nhập bằng `521H0092` vào thấy đúng tên, số dư 15.000.000 ₫
và khoản học phí 7.000.000 `UNPAID`; bấm [Thanh toán] mở được modal; 4 màn hình đi lại được với
nhau; không có URL API nào viết tay trong code.

---

## 4. TASK-C — api-gateway + payment-service (Katie, đang làm)

| Mục | Nội dung |
|---|---|
| Người làm | **Katie** |
| Bắt đầu → Deadline | **04/09/2026 → 07/09/2026** |
| Nhánh | `feat/api-gateway` → `feat/fr03-fr08-payment-service` |
| Trạng thái | 🔄 Đang làm |

- api-gateway `:8000` — cổng duy nhất frontend gọi vào, route sang 6 service, kiểm JWT, CORS.
  **Ưu tiên làm trong ngày đầu** để B có `:8000` mà test giao diện.
- payment-service `:8004` — orchestrator: tạo giao dịch, xác thực OTP, gửi lại OTP, hủy, lịch sử,
  FSM trạng thái + **job quét giao dịch hết hạn 5–10 giây** (FR-03 → FR-08).
- Cập nhật `scripts/run_dev.bat`, `scripts/test_api.py`, `frontend/js/endpoints.js` khi cần
  (đây là các file dùng chung — A và B không sửa).

**Vùng file của Katie:** `services/payment-service/**`, `services/api-gateway/**`,
`services/shared/**`, `scripts/**`, `frontend/js/endpoints.js`, `frontend/js/api-client.js`, `db/**`, `docs/**`.

---

## 5. Bảng ranh giới file toàn nhóm (tra nhanh khi không rõ)

| File / thư mục | A | B | Katie |
|---|---|---|---|
| `services/otp-service/**`, `services/notification-service/**` | ✅ sửa | ⛔ | 👀 đọc |
| `frontend/*.html`, `frontend/css/**`, `frontend/js/pages/**` | ⛔ | ✅ sửa | 👀 đọc |
| `frontend/js/endpoints.js`, `frontend/js/api-client.js` | ⛔ | 👀 chỉ đọc | ✅ sửa |
| `services/payment-service/**`, `services/api-gateway/**` | ⛔ | ⛔ | ✅ sửa |
| `services/shared/**` | ⛔ | ⛔ | ✅ sửa |
| `services/auth|payer|tuition-service/**` | ⛔ | ⛔ | ✅ sửa |
| `services/.env.example` | ✅ chỉ thêm dòng Gmail | ⛔ | ✅ sửa |
| `db/*.sql` | ⛔ | ⛔ | ✅ sửa |
| `scripts/test_otp.py`, `scripts/test_notification.py` | ✅ tạo mới | ⛔ | 👀 đọc |
| `scripts/test_api.py`, `run_dev.bat`, `check_env.py` | ⛔ | ⛔ | ✅ sửa |
| `docs/NHAT-KY-CONG-VIEC.md` | ✅ thêm entry | ✅ thêm entry | ✅ |
| `docs/PHAN-CONG-CONG-VIEC.md` | ✅ tick TASK-A | ✅ tick TASK-B | ✅ |
| `docs/01`…`docs/12`, `docs/fr/**`, `README.md` | ⛔ | ⛔ | ✅ sửa |

Cần sửa file ngoài vùng của mình → **nhắn nhóm trước**, để Katie sửa hoặc thống nhất thời điểm,
tránh 2 người sửa cùng file cùng lúc gây conflict.

---

## 6. Hợp đồng chung — không ai được tự đổi

| Hạng mục | Chốt ở đâu | Ghi chú |
|---|---|---|
| Tên + đường dẫn endpoint | [docs/11](11-tai-lieu-api-endpoint-resource.md) + [docs/03](03-thiet-ke-rest-api.md) | Muốn đổi → nhắn nhóm, sửa tài liệu trước, rồi mới sửa code |
| Cấu trúc lỗi + mã lỗi | [docs/10](10-quy-dinh-ma-phan-hoi.md) | Luôn `{"error": {code, message, detail}}`; không tự đặt mã mới |
| Trạng thái nghiệp vụ | [docs/10](10-quy-dinh-ma-phan-hoi.md) mục 5 | 7 trạng thái payment, 3 trạng thái tuition — không thêm bớt |
| Schema database | `db/02-schema.sql` | `otps` giữ status vòng đời; chỉ tạo 1 payment active/uid và 1 OTP ACTIVE/uid/payment |
| Cổng service | 8000 gateway · 8001 auth · 8002 payer · 8003 tuition · 8004 payment · 8005 otp · 8006 notification | Không tự đổi port |
| Xác thực nội bộ | header `X-Internal-Token` (giá trị trong `services/.env`) | Endpoint `/internal/*` thiếu header → 403 |
| Xác thực người dùng | `Authorization: Bearer <JWT>`; uid luôn lấy từ JWT | Client **không bao giờ** truyền `uid`/`student_id` |

---

## 7. Nhắc lại 3 việc dễ quên nhất

1. **Tick output** trong file này ngay khi làm xong từng mục — đây là bằng chứng tiến độ.
2. **Ghi entry nhật ký** trước khi mở PR: đã làm gì · công nghệ/thuật toán · liên kết bên thứ 3 ·
   **cần gì để người khác pull về chạy được**.
3. **Không sửa file ngoài vùng của mình** — 90% conflict của nhóm đến từ việc này.








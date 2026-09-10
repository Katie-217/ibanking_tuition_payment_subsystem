# 08 — Hướng dẫn chạy test API

> Mục tiêu: xác nhận API **đã hoạt động đúng** (data trả về đúng với thiết kế ở
> [03-thiet-ke-rest-api.md](03-thiet-ke-rest-api.md) và [04-thiet-ke-co-so-du-lieu.md](04-thiet-ke-co-so-du-lieu.md)
> trước khi bắt đầu build UI.

**Trạng thái hiện tại:** đã code xong **3 service nền tảng** (auth :8001, payer :8002, tuition :8003).
Flow test được toàn bộ vòng lõi: *đăng nhập → lấy thông tin user → lấy payer/số dư → lấy học phí*
kèm các endpoint nội bộ (trừ tiền / hoàn tiền / khóa học phí) để kiểm tra nghiệp vụ chống
trùng giao dịch. Payment-service, OTP-service, notification-service, api-gateway vẫn đang phát triển.

---

## 1. Điều kiện tiên quyết

| # | Mục | Yêu cầu |
|---|-----|---------|
| 1 | SQL Server | Đã cài và đang chạy (bản Developer/Express đều được) |
| 2 | ODBC Driver | **ODBC Driver 18 for SQL Server** |
| 3 | Python | 3.10 trở lên |
| 4 | Thư viện | `pip install -r services/requirements.txt` |
| 5 | Database | Đã chạy 3 file `db/01-create-databases.sql`, `db/02-schema.sql`, `db/03-seed.sql` |
| 6 | Mật khẩu demo | Đã sinh hash bcrypt (mục 4 bên dưới) |

---

## 2. Cài thư viện Python

```bat
rem mở terminal TẠI THƯ MỤC GỐC DỰ ÁN (thư mục chứa README.md) rồi gõ:
pip install -r services\requirements.txt
```

Gói chính: `fastapi`, `uvicorn[standard]`, `pyodbc` (kết nối SQL Server), `PyJWT` (JWT),
`bcrypt` (hash mật khẩu), `httpx` (test API), `python-dotenv`.

> ⚠️ Nếu trước đây từng `pip install jwt` → gỡ ngay (`pip uninstall jwt`) vì gói cũ này
> đè lên PyJWT và làm code lỗi. Script `check_env.py` sẽ cảnh báo vụ này.

---

## 3. Tạo database + dữ liệu demo (làm 1 lần)

Mở **SSMS**, đăng nhập sa, chạy lần lượt 3 file (đủ 6 database):

| File | Việc làm | Chạy lại được? |
|------|----------|----------------|
| `db/01-create-databases.sql` | Tạo 6 database: AuthDB, PayerDB, TuitionDB, PaymentDB, OTPDB, NotificationDB | ✅ bỏ qua DB đã có |
| `db/02-schema.sql` | Tạo toàn bộ bảng + ràng buộc (CHECK, UNIQUE, filtered index) | ✅ bỏ qua bảng đã có |
| `db/03-seed.sql` | Nạp 3 tài khoản demo, hồ sơ payer, trường/khoa/ngành/hệ, học phí | ✅ bỏ qua bản ghi đã có |

---

## 4. Sinh mật khẩu hash bcrypt (bắt buộc)

Bảng `user_credentials` lưu **hash bcrypt**, không lưu mật khẩu thô. Seed để placeholder `TO_BE_SET`
nên phải thay bằng hash thật — mật khẩu demo của cả 3 tài khoản là **`abc12345`**:

```bat
rem tại thư mục gốc dự án:
set PYTHONPATH=%CD%\services
python db\generate_password_hashes.py
```

Script in ra các dòng dạng:

```sql
UPDATE AuthDB.dbo.user_credentials
SET password_hash = N'$2b$12$...'
WHERE uid = (SELECT uid FROM AuthDB.dbo.users WHERE username = N'521H0092');
-- Hai tài khoản còn lại dùng cùng mẫu WHERE theo username tương ứng.
```

**Dán 3 dòng này vào SSMS chạy.** Nếu bỏ qua bước này, login luôn báo 401.

---

## 5. Tạo file cấu hình `.env`

Copy file mẫu thành `services\.env` rồi sửa `DB_PWD` (mật khẩu sa):

```bat
copy services\.env.example services\.env
notepad services\.env
```

```ini
DB_SERVER=localhost
DB_UID=sa
DB_PWD=Mật_khẩu_sa_của_bạn
DB_DRIVER=ODBC Driver 18 for SQL Server
JWT_SECRET=ibanking-gk-demo-2025
JWT_EXPIRES_MINUTES=30
INTERNAL_TOKEN=internal-token-gk-demo
```

---

## 6. Kiểm tra môi trường (khuyên chạy)

```bat
python scripts\check_env.py
```

Kết quả mong đợi — toàn bộ ✅ và dòng cuối:

```
✅ Môi trường OK — chạy tiếp: scripts\run_dev.bat rồi python scripts/test_api.py
```

Script kiểm tra: gói Python → ODBC Driver → `.env` → kết nối 6 database + đếm dòng từng bảng
→ mật khẩu còn placeholder `TO_BE_SET` hay không.

---

## 7. Khởi động 3 service

```bat
scripts\run_dev.bat
```

Mở 3 cửa sổ CMD riêng:

| Service | Port | Cửa sổ |
|---------|------|--------|
| auth-service | 8001 | `iBanking-auth-service :8001` |
| payer-service | 8002 | `iBanking-payer-service :8002` |
| tuition-service | 8003 | `iBanking-tuition-service :8003` |

Mỗi cửa sổ in ra dòng `Uvicorn running on http://127.0.0.1:8001 ...` là service đã sẵn sàng.
Đóng cửa sổ là tắt service; muốn khởi động lại thì chạy lại batch.

---

## 8. Test bằng Swagger UI (tự tay bấm thử)

Swagger UI có sẵn ở từng service, **không cần cài Postman**:

| Service | Swagger |
|---------|---------|
| auth-service | http://localhost:8001/docs |
| payer-service | http://localhost:8002/docs |
| tuition-service | http://localhost:8003/docs |

Thử luồng chính:
1. Vào http://localhost:8001/docs → `POST /auth/login` → **Try it out**, nhập body:
   ```json
   {"username": "521H0092", "password": "abc12345"}
   ```
   → status 200, copy giá trị `token`.
2. Bấm nút **Authorize** (góc trên phải), dán `token` vào (Swagger tự thêm `Bearer ...`).
3. Gọi `GET /auth/me` → 200, thấy `username = 521H0092` (uid là giá trị tự sinh thực tế).
4. Sang http://localhost:8002/docs → `GET /payers/me` (Authorize lại bằng token cũ) → `available_balance = 15000000`.
5. Sang http://localhost:8003/docs → `GET /tuition/me` → hồ sơ sinh viên (trường/khoa/ngành/hệ) + danh sách học phí.

### Test nhanh bằng curl

```bat
rem Đăng nhập lấy token
curl -s -X POST http://localhost:8001/auth/login -H "Content-Type: application/json" -d "{\"username\":\"521H0092\",\"password\":\"abc12345\"}"

rem Gọi API có bảo vệ (thay <TOKEN> bằng token ở trên)
curl -s http://localhost:8002/payers/me -H "Authorization: Bearer <TOKEN>"
curl -s http://localhost:8003/tuition/me -H "Authorization: Bearer <TOKEN>"

rem Endpoint nội bộ cần X-Internal-Token (giá trị trong services\.env)
curl -s -X POST http://localhost:8002/internal/balance/capture -H "X-Internal-Token: internal-token-gk-demo" -H "Content-Type: application/json" -d "{\"payment_id\": 888001, \"uid\": 2, \"amount\": 1500000}"
```

---

## 9. Chạy bộ test tự động (khuyên dùng)

```bat
python scripts\test_api.py
```

Kết quả mong đợi: **18/18 PASS**. Bảng mô tả từng test case:

| Test | Kiểm tra gì | Kết quả mong đợi |
|------|-------------|------------------|
| T01 | /health của 3 service | 200 `{"status":"ok"}` |
| T02 | Login đúng MSSV + đúng mật khẩu | 200, có `token` |
| T03 | Login sai mật khẩu | 401 `AUTH_INVALID_CREDENTIALS` |
| T04 | Login MSSV sai định dạng (521H009) | 400 `VALIDATION_ERROR` |
| T05 | /auth/me thiếu token | 401 `AUTH_REQUIRED` |
| T06 | /auth/me có token | 200, `uid=1`, `username=521H0092` |
| T07 | /payers/me | 200, `available_balance=15000000` |
| T08a | /tuition/me đúng chủ sở hữu | `student_id=521H0092`, trường TDTU |
| T08b | Khoản 2025-2026-HK1 | `amount=7000000`, `UNPAID` |
| T08c | Đủ trường/khoa/ngành/hệ + mã hệ | các khối `school/faculty/major/edu_system` có dữ liệu |
| T09 | Trừ tiền nội bộ uid2 (2.000.000 − 1.500.000) | 200, `balance_after=500000` |
| T10 | Trừ lại **cùng** payment_id | idempotent, balance vẫn 500.000 (không trừ 2 lần) |
| T11 | Hoàn tiền | balance về 2.000.000 |
| T12 | Hoàn lại cùng payment_id | idempotent, không cộng 2 lần |
| T13 | uid3 (1.000.000) trừ 5.000.000 | 422 `INSUFFICIENT_BALANCE` |
| T14 | Gọi nội bộ thiếu `X-Internal-Token` | 403 `FORBIDDEN` |
| T15 | Khóa tuition (UNPAID→PAYING) | 200, `status=PAYING` |
| T16 | Internal get tuition | 200, trạng thái `PAYING` |
| T17 | Mở khóa tuition (PAYING→UNPAID) | 200, `status=UNPAID` |
| T18 | **uid khác** khóa tuition của uid1 | 403 (BR-04 — chỉ trả tiền học phí của chính mình) |

> Test **chạy lại được nhiều lần**: T09–T12 kết thúc bằng hoàn tiền (balance về đúng 2.000.000),
> T15–T17 kết thúc bằng mở khóa (tuition về UNPAID). Do không có test nào để lại dữ liệu bẩn.

---

## 10. Ba tài khoản demo

Mật khẩu tất cả: **`abc12345`**

| MSSV (username) | Họ tên | Số dư | Học phí chưa nộp | Mục đích test |
|-----------------|--------|-------|------------------|---------------|
| `521H0092` | Nguyễn Văn A | 15.000.000 | 7.000.000 (HK1) | Luồng thành công |
| `522H0145` | Trần Thị B | 2.000.000 | 1.500.000 (HK1) | Luồng thành công, hụt dư nhẹ |
| `523H0201` | Lê Minh C | 1.000.000 | 5.000.000 (HK1) + 1 khoản PAID | Test hết tiền + học phí đã nộp |

---

## 11. Danh sách endpoint đã chạy được

### auth-service (:8001)

| Method | Path | Bảo vệ | Mô tả |
|--------|------|--------|-------|
| POST | `/auth/login` | — | Đăng nhập MSSV + mật khẩu → JWT |
| POST | `/auth/logout` | Bearer | Đăng xuất (stateless) |
| GET | `/auth/me` | Bearer | Thông tin user từ JWT |
| GET | `/health` | — | Kiểm tra sống + kết nối AuthDB |

### payer-service (:8002)

| Method | Path | Bảo vệ | Mô tả |
|--------|------|--------|-------|
| GET | `/payers/me` | Bearer | Hồ sơ người nộp + số dư (theo uid từ JWT) |
| POST | `/internal/balance/capture` | X-Internal-Token | Trừ tiền nguyên tử (chống dư âm), idempotent theo payment_id |
| POST | `/internal/balance/release` | X-Internal-Token | Hoàn tiền bù trừ, idempotent theo payment_id |
| GET | `/health` | — | Kiểm tra sống + kết nối PayerDB |

### tuition-service (:8003)

| Method | Path | Bảo vệ | Mô tả |
|--------|------|--------|-------|
| GET | `/tuition/me` | Bearer | Hồ sơ sinh viên (trường/khoa/ngành/hệ) + các khoản học phí |
| GET | `/internal/tuitions/{id}?uid=` | X-Internal-Token | Lấy 1 khoản học phí + kiểm tra chủ sở hữu |
| POST | `/internal/tuitions/{id}/lock` | X-Internal-Token | UNPAID → PAYING (chống thanh toán 2 lần song song) |
| POST | `/internal/tuitions/{id}/paid` | X-Internal-Token | PAYING → PAID + lưu payment_id |
| POST | `/internal/tuitions/{id}/release` | X-Internal-Token | PAYING → UNPAID (bù trừ khi thất bại/hủy) |
| GET | `/health` | — | Kiểm tra sống + kết nối TuitionDB |

Đầy đủ 24 endpoint còn lại (payment, OTP, notification, gateway) đã thiết kế trong
[03-thiet-ke-rest-api.md](03-thiet-ke-rest-api.md) — sẽ code ở giai đoạn tiếp theo.

---

## 12. Lỗi thường gặp và cách xử lý

| Hiện tượng | Nguyên nhân | Cách xử lý |
|------------|-------------|------------|
| `IM002 ... data source name not found` | Thiếu ODBC Driver 18 | Cài driver, rồi `python scripts/check_env.py` kiểm tra lại |
| `Login failed for user 'sa'` | Sai mật khẩu / chưa bật SQL Auth | Sửa `DB_PWD` trong `services\.env`; bật SQL Server Authentication trong SSMS |
| `Cannot open database "AuthDB"` | Chưa chạy `db/01` | Mở SSMS chạy `db/01-create-databases.sql` |
| `Invalid object name 'dbo.users'` | Chưa chạy schema | Chạy `db/02-schema.sql` |
| Login luôn 401 dù đúng mật khẩu | Chưa thay hash `TO_BE_SET` | Làm lại **mục 4** ở trên |
| `ModuleNotFoundError: No module named 'shared'` | Thiếu PYTHONPATH | Chạy service qua `scripts\run_dev.bat` (đã set sẵn) |
| Cửa sổ CMD 9009 `python` không nhận | Python chưa có trong PATH | Cài Python có tick "Add to PATH", hoặc gõ `py -3` thay `python` |
| Test T01 báo ConnectError | Service chưa chạy | Chạy `scripts\run_dev.bat` trước |
| `pyodbc.ProgrammingError` trong PayerDB | Bảng `balance_ledger` chưa tạo | Chạy lại `db/02-schema.sql` |

---

## 13. Trình tự test khuyến nghị

```
pip install → tạo DB (01→02→03) → sinh hash mật khẩu (mục 4) → tạo .env
   → check_env.py (toàn ✅) → run_dev.bat (3 cửa sổ) → test_api.py (18 PASS)
   → tự tay thử Swagger UI / curl cho quen dữ liệu trả ra → xem quan hệ bảng bằng dbdiagram.io
```

Sau khi xác nhận xong dữ liệu API đúng → mới chuyển sang build UI (frontend gọi API qua lớp
trung gian `frontend/js/endpoints.js`, không gọi URL trực tiếp).
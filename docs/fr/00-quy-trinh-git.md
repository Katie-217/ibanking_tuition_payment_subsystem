# 00 — Quy trình làm việc với Git / GitHub (nhóm 3 người)

> Áp dụng cho **mọi chức năng** (mỗi file FR-xx đều phải tuân theo quy trình này).
>
> Quy tắc cốt lõi:
> 1. **Mỗi chức năng = 1 nhánh riêng.**
> 2. Trước khi làm chức năng mới: **quét lại dự án + kiểm tra remote + pull `main` mới nhất**.
> 3. **Giải quyết xong conflict mới được push.**
> 4. Push nhánh feature → **mở PR, viết mô tả đã làm, chờ thành viên khác duyệt** (không tự merge).
> 5. **Cập nhật [file nhật ký công việc](../NHAT-KY-CONG-VIEC.md) khi bắt đầu làm và khi làm xong** (mục 8).
>
> chạy **tại thư mục gốc dự án** (thư mục chứa `README.md`) — mở terminal ở đó rồi gõ lệnh,
> hoặc bấm phải vào thư mục → *Open Git Bash here*. Đường dẫn trong tài liệu luôn viết **tương đối**:
> `services/.env`, `scripts/run_dev.bat`, `db/02-schema.sql`.

---

## 1. Kết nối local ↔ remote (mỗi người làm 1 lần trên máy mình)

**Repo GitHub của nhóm:** cung cấp thông qua group chung

Người đã có sẵn thư mục dự án trên máy (không clone) → chỉ cần nối remote 1 lần:

```bash
# tại thư mục gốc dự án
git remote add origin <link-github>
git remote -v                      # xác nhận origin đúng repo của nhóm
```

Người chưa có code → clone về:

```bash
git clone <link-github>
cd ibanking_tuition_payment_subsystem
```

### 1.1 Chuẩn bị môi trường (cả 3 người, sau khi có code)

```bash
cp services/.env.example services/.env    # Windows CMD: copy services\.env.example services\.env
# mở services/.env, điền DB_PWD của SQL Server trên MÁY MÌNH
pip install -r services/requirements.txt
python scripts/check_env.py
```

> `services/.env` đã nằm trong `.gitignore` → mỗi người có mật khẩu SQL Server riêng, không bao giờ
> commit lên GitHub. File `services/.env.example` (không chứa giá trị thật) thì được commit.

---

## 2. Quy ước đặt tên nhánh

Cấu trúc: **`<loại>/<mã-fr>-<mô-tả-ngắn-gạch-nối>`**

```
feat/fr03-create-payment-otp
 │     │        └── mô tả ngắn, tiếng Anh, gạch nối, không dấu
 │     └── mã chức năng trong docs/fr (fr01…fr08); nhánh không thuộc FR nào thì bỏ phần này
 └── loại công việc (xem bảng dưới)
```

### 2.1 Tiền tố loại nhánh — dùng khi nào

| Tiền tố | Dùng khi | Ví dụ tên nhánh |
|---|---|---|
| `feat/` | Làm **chức năng mới** (đa số các FR) | `feat/fr03-create-payment-otp` |
| `fix/` | **Sửa lỗi** của chức năng đã merge | `fix/fr04-otp-expired-not-released` |
| `docs/` | Chỉ **sửa/thêm tài liệu**, không đụng code | `docs/update-api-catalog` |
| `refactor/` | **Dọn code**, đổi cấu trúc mà **không đổi hành vi** | `refactor/shared-db-connection` |
| `test/` | Thêm/sửa **test**, script kiểm thử | `test/concurrency-double-payment` |
| `chore/` | Việc phụ trợ: cấu hình, dependency, `.gitignore`, script chạy | `chore/add-docker-compose` |

### 2.2 Nhánh cho 8 chức năng của dự án

| FR | Chức năng | Nhánh |
|---|---|---|
| FR-01 | Đăng nhập / đăng xuất | `feat/fr01-authentication` |
| FR-02 | Trang chính (hồ sơ + số dư + học phí) | `feat/fr02-dashboard` |
| FR-03 | Tạo giao dịch & gửi OTP | `feat/fr03-create-payment-otp` |
| FR-04 | Xác thực OTP & hoàn tất thanh toán | `feat/fr04-verify-otp` |
| FR-05 | Gửi lại OTP | `feat/fr05-resend-otp` |
| FR-06 | Hủy giao dịch | `feat/fr06-cancel-payment` |
| FR-07 | Lịch sử giao dịch | `feat/fr07-payment-history` |
| FR-08 | Job quét giao dịch hết hạn | `feat/fr08-sweep-expired-job` |

### 2.3 Chỉ có 2 loại nhánh tồn tại lâu dài

| Nhánh | Vai trò |
|---|---|
| `main` | Code ổn định, **chỉ nhận code qua PR đã được duyệt** |
| `feat/…`, `fix/…`, … | Nhánh tạm của 1 chức năng — merge xong thì xóa |

---

## 3. Quy ước thông điệp commit (viết **tiếng Anh** cho đồng bộ)

Cấu trúc: **`<loại>(<phạm-vi>): <mô tả ngắn, tiếng Anh, thể hiện tại, không dấu chấm cuối>`**

```
feat(fr03): create payment and send OTP email
 │     │      └── viết ở thể mệnh lệnh: "add", "fix", "update" — KHÔNG "added"/"adding"
 │     └── phạm vi: mã FR (fr01…fr08) hoặc tên service/module (auth, payer, tuition, docs, db)
 └── loại commit
```

### 3.1 Tiền tố loại commit — dùng khi nào

| Tiền tố | Dùng khi | Ví dụ commit |
|---|---|---|
| `feat:` | Thêm **chức năng/endpoint mới** cho người dùng | `feat(fr03): add POST /payments endpoint` |
| `fix:` | **Sửa lỗi** (bug, sai logic, sai mã response) | `fix(payer): prevent negative balance on concurrent capture` |
| `docs:` | Chỉ **tài liệu** (`README.md`, `docs/**`), không đổi code | `docs(fr): add FR-05 resend OTP specification` |
| `refactor:` | Đổi cấu trúc code, **hành vi không đổi** | `refactor(shared): extract error factory functions` |
| `test:` | Thêm/sửa test, script kiểm thử | `test(api): add concurrency test for double payment` |
| `chore:` | Cấu hình, dependency, script, `.gitignore` — không phải code nghiệp vụ | `chore: add .gitignore and .gitattributes` |
| `style:` | Format, thụt lề, đặt tên — **không đổi logic** | `style(frontend): format dashboard.js with prettier` |
| `perf:` | Tối ưu hiệu năng | `perf(tuition): add index on student_id` |
| `db:` | Thay đổi schema/seed SQL Server (quy ước riêng của nhóm) | `db: add filtered unique index on payments` |

### 3.2 Nguyên tắc commit

- **Nhỏ, một mục đích** — 1 commit làm 1 việc; đừng gộp "sửa UI + đổi schema + thêm API".
- Mỗi commit phải để dự án **chạy được**: `python scripts/test_api.py` không tệ hơn trước đó.
- Mô tả **tiếng Anh, ngắn ≤ 72 ký tự**, không dấu tiếng Việt (tránh lỗi font khi xem trên máy khác).
- Cần giải thích dài → viết vào phần thân commit (dòng trống rồi mới viết), hoặc để trong PR.

---

## 4. Quy trình bắt đầu 1 chức năng mới (BẮT BUỘC, làm trước khi viết dòng code đầu tiên)

```bash
# (a) QUÉT LẠI TOÀN BỘ DỰ ÁN 1 LẦN
git status                      # có file đang sửa dở không? phải sạch
git log --oneline -8            # xem 8 commit gần nhất, biết người khác vừa làm gì
git branch -a                   # xem nhánh của cả nhóm, tránh trùng việc
# Đọc lại file FR sắp làm trong docs/fr + docs/03 (API) + docs/10 (mã lỗi)

# (b) KIỂM TRA REMOTE
git remote -v                   # origin phải trỏ đúng repo GitHub của nhóm
git fetch origin                # lấy thông tin nhánh mới nhất từ GitHub

# (c) KÉO CODE MỚI VỀ — ĐẢM BẢO KHÔNG CONFLICT
git switch main
git pull origin main            # phải chạy THÀNH CÔNG, không được để lại conflict
git status                      # phải sạch: "nothing to commit, working tree clean"

# (d) TẠO NHÁNH RIÊNG CHO CHỨC NĂNG
git switch -c feat/frXX-short-description

# (e) VÀO FILE NHẬT KÝ ĐÁNH DẤU ĐANG LÀM
#     docs/NHAT-KY-CONG-VIEC.md → mục 2: đổi trạng thái sang 🔄 Đang làm,
#     ghi ngày bắt đầu + tên nhánh (xem mục 8 tài liệu này)
```

Vì sao bắt buộc bước (c): nhánh mới luôn cắt ra từ `main` **mới nhất** → gần như không đụng
conflict với 2 bạn còn lại. Nếu `git pull` ở (c) báo conflict nghĩa là `main` đang không sạch →
xử lý xong mới được làm tiếp.

### Chia việc cho 3 người để ít conflict nhất

| Thành viên | Vùng file chính | Tránh sửa |
|---|---|---|
| A | `services/payment-service/**`, `services/otp-service/**` | file của B, C |
| B | `services/auth-service/**`, `services/payer-service/**`, `services/tuition-service/**` | file của A, C |
| C | `frontend/**` (trừ `endpoints.js`), `docs/**` | file của A, B |

`frontend/js/endpoints.js`, `services/shared/**`, `db/02-schema.sql`, `README.md` là **file dùng
chung** → ai sửa thì nói trong nhóm trước, sửa gọn, merge sớm để 2 người kia pull về ngay.

---

## 5. Trước khi push (BẮT BUỘC — giải quyết xong conflict mới được push)

```bash
# (1) Tự kiểm tra lại
python scripts/check_env.py
python scripts/test_api.py                 # phải PASS hết như trước khi bạn sửa

# (2) CẬP NHẬT NHẬT KÝ CÔNG VIỆC (bắt buộc — xem mục 8)
#     docs/NHAT-KY-CONG-VIEC.md:
#       - mục 2: đổi trạng thái sang 🧪 Chờ review
#       - mục 3: nếu bạn thêm thư viện / biến .env / đổi schema DB thì ghi 1 dòng
#       - mục 4: thêm 1 entry theo mẫu (đã làm gì, công nghệ, bên thứ 3, cách chạy)

# (3) Commit công việc của mình
git add <cac-file-cua-ban> docs/NHAT-KY-CONG-VIEC.md
git status                                 # KIỂM TRA không có services/.env
git commit -m "feat(fr03): add POST /payments endpoint"

# (4) Đồng bộ main mới nhất vào nhánh của mình
git fetch origin
git merge origin/main                      # (hoặc: git rebase origin/main nếu nhóm thống nhất dùng rebase)

# (5) NẾU CÓ CONFLICT → xử lý XONG mới push
git status                                 # xem "both modified: <file>"
#   mở từng file, tìm dấu  <<<<<<<   =======   >>>>>>>
#   giữ lại đúng nội dung cần, XÓA HẾT các dấu đó
git add <file-da-sua>
git commit                                 # hoàn tất merge (hoặc: git rebase --continue)
python scripts/test_api.py                 # chạy test LẠI sau khi giải conflict

# (6) Push nhánh feature (KHÔNG push thẳng main)
git push -u origin feat/frXX-short-description
```

### Quy tắc vàng

| RULE | Nội dung |
|---|---|
| R1 | Mỗi chức năng 1 nhánh riêng, không code lẫn sang nhánh của người khác |
| R2 | Bắt đầu chức năng mới = quét lại dự án + kiểm tra remote + **pull `main`** trước |
| R3 | **Giải quyết xong toàn bộ conflict + chạy lại test mới được push** |
| R4 | Chỉ push nhánh feature; **không** push thẳng `main`; **không** `git push --force` |
| R5 | Push xong → mở PR, mô tả rõ đã làm gì, **chờ người khác duyệt**, không tự merge |
| R6 | Không commit `services/.env`, không commit `logs/`, `__pycache__/`, `.venv/` |
| R7 | Commit message **tiếng Anh** theo bảng mục 3.1 |
| R8 | **Bắt đầu làm** → đánh dấu 🔄 Đang làm trong `docs/NHAT-KY-CONG-VIEC.md`; **làm xong** → ghi entry nhật ký đầy đủ (mục 8) |
| R9 | Thêm thư viện / biến `.env` / đổi schema DB → **phải** ghi vào mục 3 của file nhật ký để 2 người kia pull về chạy được ngay |

---

## 6. Mở Pull Request & hoàn tất

1. Lên GitHub → **Pull requests** → **New pull request** → base `main` ← compare `feat/frXX-…`.
2. Tiêu đề PR viết như commit chuẩn: `feat(fr03): create payment and send OTP email`.
3. Mô tả PR theo mẫu (phần nội dung có thể viết tiếng Việt cho dễ trao đổi):

   ```markdown
   ## Đã làm được gì
   - [x] Backend: POST /payments — khóa tuition, trừ tiền, sinh OTP, gửi email (FR-03)
   - [x] Frontend: modal xác nhận + màn hình nhập OTP
   - [ ] Chưa làm: đếm ngược OTP trên mobile (sẽ làm ở PR sau)

   ## Đã tự kiểm tra
   - `python scripts/check_env.py` → OK
   - `python scripts/test_api.py` → PASS toàn bộ
   - Thử tay trên Swagger: tạo payment cho 521H0092 → nhận email OTP

   ## API thay đổi
   | Method | Endpoint | Ghi chú |
   |---|---|---|
   | POST | /payments | endpoint mới |

   ## Liên quan
   - Tài liệu: `docs/fr/FR-03-tao-giao-dich-gui-otp.md`
   - Ràng buộc: BR-05 → BR-08, BR-10
   - Nhật ký: đã cập nhật `docs/NHAT-KY-CONG-VIEC.md` (mục 2 trạng thái + mục 4 entry)
   ```

4. Gán 1 thành viên khác làm **Reviewer** → **chờ approve mới merge** (không tự merge PR của mình).
   Reviewer kiểm: đúng tài liệu FR chưa, mã response đúng `docs/10` chưa, test còn PASS không,
   **nhật ký công việc đã cập nhật chưa**.
5. Sau khi PR được merge, dọn nhánh và đồng bộ lại:

   ```bash
   git switch main
   git pull origin main
   git branch -d feat/frXX-short-description             # xóa nhánh local
   git push origin --delete feat/frXX-short-description  # xóa nhánh trên GitHub
   ```

6. Bắt đầu chức năng tiếp theo → quay lại **mục 4** từ đầu.

---

## 7. Xử lý tình huống hay gặp

| Tình huống | Cách xử lý |
|---|---|
| Push bị từ chối `rejected — non-fast-forward` | Có người push trước: `git fetch origin` → `git merge origin/main` → giải conflict → test → push lại |
| Lỡ commit `services/.env` | `git rm --cached services/.env` → commit lại; **đổi ngay mật khẩu SQL Server** nếu đã push |
| Đang làm dở mà cần đổi nhánh gấp | `git stash` → đổi nhánh → xong việc → `git switch` về → `git stash pop` |
| Commit sai nội dung/thông điệp (chưa push) | `git commit --amend` (chỉ dùng khi **chưa** push) |
| Muốn bỏ hết thay đổi 1 file (chưa commit) | `git restore <file>` — mất thay đổi của file đó, cân nhắc trước |
| Xem ai sửa dòng nào | `git log -p <file>` hoặc `git blame <file>` |

---

## 8. Nhật ký công việc (BẮT BUỘC — [docs/NHAT-KY-CONG-VIEC.md](../NHAT-KY-CONG-VIEC.md))

Mọi tiến độ nằm ở **1 file nhật ký duy nhất**: `docs/NHAT-KY-CONG-VIEC.md`; chi tiết task từng
người (mô tả, output phải tick, vùng file được sửa) nằm ở **[docs/PHAN-CONG-CONG-VIEC.md](../PHAN-CONG-CONG-VIEC.md)**.

**Thứ tự đọc khi ngồi vào làm:** nhật ký (biết người khác đã làm gì, phải cài thêm gì) →
file phân công (task của mình) → code → tick output trong file phân công + ghi entry nhật ký.

### 8.1 Ba thời điểm phải vào cập nhật

| Thời điểm | Việc phải làm trong file nhật ký |
|---|---|
| **Khi bắt đầu làm** (ngay sau khi tạo nhánh) | Mục 2: đổi trạng thái sang 🔄 **Đang làm**, ghi **ngày bắt đầu** + **tên nhánh** |
| **Khi làm xong** (trước khi mở PR) | Mục 2: đổi 🧪 **Chờ review** · Mục 4: thêm **1 entry đầy đủ** theo mẫu · Mục 3: ghi thay đổi ảnh hưởng người khác (nếu có) · **tick output** trong file phân công |
| **Sau khi PR được merge** | Mục 2: đổi ✅ **Đã xong** + điền số PR |

Bị vướng không làm tiếp được → đổi ⛔ **Bị chặn** và ghi rõ vướng gì, cần ai giúp (đừng để trạng
thái treo 🔄 nhiều ngày, người khác không biết mà hỗ trợ).

### 8.2 Entry nhật ký phải trả lời đủ 4 câu

| # | Câu hỏi | Vì sao cần |
|---|---|---|
| 1 | **Đã làm được gì?** (endpoint nào, màn hình nào chạy được) | Nhóm biết tiến độ thật, reviewer biết cần xem gì |
| 2 | **Dùng công nghệ / thuật toán gì?** | Bảo vệ đồ án phải giải thích được kỹ thuật (khóa DB, FSM, idempotency, bcrypt, JWT…) |
| 3 | **Liên kết bên thứ 3 nào?** (Gmail SMTP, thư viện ngoài, API ngoài — cần khóa/bí mật gì) | Người khác biết phải xin/khai báo khóa gì mới chạy được |
| 4 | **Cần gì để người khác pull về chạy được?** thư viện mới · biến `.env` mới · script DB phải chạy · service/port cần bật · lệnh chạy + lệnh test | Đây là phần **quan trọng nhất** — thiếu là 2 người kia pull về bị lỗi và mất buổi để dò |

Mẫu entry copy sẵn nằm ở đầu mục 4 của file nhật ký. Ghi nhật ký **cùng PR** với code
(`git add docs/NHAT-KY-CONG-VIEC.md`), commit dạng `docs(log): update work log for FR-03`.

### 8.3 Vì sao bắt buộc

- Mỗi người làm trên **máy riêng, đường dẫn riêng, mật khẩu SQL Server riêng** — thứ chạy được ở
  máy bạn chưa chắc chạy ở máy người khác; mục 3 + câu hỏi 4 chính là cầu nối đó.
- File nhật ký là bằng chứng phân công + tiến độ khi báo cáo/bảo vệ đồ án.
- Reviewer đọc entry là biết PR làm gì, không phải dò từng dòng diff.
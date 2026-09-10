# Tài liệu 01 — Làm rõ yêu cầu & Scope

> Tổng hợp từ: `DỰ ÁN GIỮA KỲ.md` + `làm rõ yêu cầu.txt` + `plan phát triển.txt` + các quyết định dự án (Project-Specific Decision).

## 1. Mục tiêu phân hệ

Mô phỏng phân hệ **đóng học phí** của ứng dụng **iBanking** cho sinh viên **TDTU**:

- Người dùng đăng nhập, dùng **số dư tài khoản của chính mình** thanh toán **toàn bộ** khoản học phí **của chính mình**.
- **Không có chức năng đăng ký tài khoản**, không nạp tiền — số dư được set cứng trong DB và chỉ thay đổi khi thanh toán.
- **Không cho phép** thanh toán hộ sinh viên khác (khác với mô tả gốc của đề bài, đã bị thu hẹp bởi *Project-Specific Decision*).

## 2. Đối tượng & định danh

| Đối tượng | Định danh | Ghi chú |
|---|---|---|
| Người dùng (User) | `uid` | Khóa nội bộ, dùng để liên kết các bảng giữa các service |
| Username | `username` | **Chuẩn MSSV TDTU**, ví dụ `521H0092` (xem §2.1) |
| Sinh viên (Student) | `student_id` (MSSV) | Sinh viên TDTU có hồ sơ học phí |
| Người nộp tiền (Payer) | `uid` | Chính là user đang đăng nhập (quan hệ 1–1) |
| Khoản học phí (Tuition) | `tuition_id` | Một student có thể có nhiều khoản theo học kỳ |
| Giao dịch (Payment) | `payment_id` | Đơn vị quản lý FSM của thanh toán |
| Mã OTP | `otp_id` | Gắn chặt 1–1 với một payment |

### 2.1 Chuẩn username = MSSV TDTU

- Format TDTU: `521H0092` = 8 ký tự (3 số + 1 chữ + 4 số).
- **Login không cho chọn trường**, nhưng **DB phải có quan hệ MSSV ↔ trường học** — bảng `students` (bảng nhận diện MSSV) tham chiếu `schools` ← `faculties` ← `majors` + `edu_systems` (trường/khoa/ngành/hệ/mã hệ). Quy tắc giải mã MSSV thật sẽ được nạp khi có.
- Regex kiểm tra đầu vào: `^\d{3}[A-Za-z]\d{4}$` — 3 số + 1 chữ cái + 4 số = 8 ký tự (khớp `521H0092`).

### 2.2 Chuỗi định danh bắt buộc (Project-Specific Decision)

```
JWT.uid
   ↓
Authenticated User
   ↓
Payer                        →  GET /payers/me
   ↓
Own Student / Own Tuition    →  GET /tuition/me
   ↓
Payment
```

- Client **KHÔNG được** truyền `payer_uid`, `uid`, `student_id`, `MSSV`… để chọn người nộp/sinh viên khác.
- Server luôn suy ra các định danh này **từ `uid` trong JWT**.
- Mọi thông tin người nộp hiển thị trên màn hình thanh toán là **read-only**.

## 3. Phạm vi chức năng (chốt lại)

### 3.1 Xác thực (Auth)
- Chỉ cần **login** và **logout**; không đăng ký.
- `username` + `password` → trả **JWT** (chứa `uid`, `username`, `role`).
- Password được **hash** (bcrypt) và lưu ở **bảng riêng** (`user_credentials`), liên kết với bảng `users` qua `uid`.
- Số dư tài khoản **set cứng sẵn** trong DB, không quan tâm nguồn gốc.

### 3.2 Màn hình thanh toán — 3 nhóm thông tin

| Nhóm | Trường | Nguồn | Chỉnh sửa |
|---|---|---|---|
| **a. Người nộp tiền** | Họ tên, SĐT, Email | `GET /payers/me` (từ JWT uid) | Read-only |
| **b. Thông tin học phí** | MSSV, họ tên SV, số tiền còn phải nộp | `GET /tuition/me` (từ JWT uid) | Read-only, không nhập MSSV khác |
| **c. Thông tin thanh toán** | Số dư khả dụng, số tiền cần thanh toán, điều khoản | `GET /payers/me` + `GET /tuition/me` | Read-only, điều khoản có link popup |

- Điều khoản: 1 dòng text ngắn "Chấp nhận các điều khoản" + link popup; checkbox **mặc định accepted** hoặc bỏ checkbox — bấm nút Thanh toán = tự động chấp nhận.
- Nút **Xác nhận giao dịch** chỉ enable khi các thông tin đầy đủ & hợp lệ.
- **Chỉ thanh toán toàn bộ** khoản học phí — không thanh toán một phần.

### 3.3 Xác thực OTP qua email
- Xác nhận giao dịch → hệ thống gửi **OTP 6 chữ số** về **email của người nộp tiền** (Gmail SMTP).
- OTP phải:
  1. Gắn với **một giao dịch cụ thể** (cột `payment_id` — ràng buộc 1–1 khi còn hiệu lực).
  2. **Không trùng** với OTP đang hiệu lực của giao dịch khác.
  3. **Hết hạn < 5 phút**.
  4. **Chỉ dùng thành công 1 lần**.
- **Vòng đời lưu trữ:** bảng OTP giữ bản ghi và cập nhật `status` khi hết hạn, xác thực thành công, giao dịch bị hủy/thất bại/hết hạn hoặc resend; chỉ tác vụ dọn dữ liệu mới xóa bản ghi.
- Người dùng nhập OTP → xác nhận lần cuối. Hệ thống chỉ xử lý khi **OTP hợp lệ và còn hạn**.
- Có thể thêm chức năng **tự điền (auto-fill) mã** khi mail gửi thành công (phục vụ demo; mặc định tắt nếu lên production).
- Giới hạn số lần nhập sai (đề xuất: 5 lần → giao dịch FAILED, phải tạo lại).

### 3.4 Xử lý giao dịch thành công (sau khi OTP hợp lệ)
1. Kiểm tra lại tính hợp lệ giao dịch + số dư khả dụng.
2. Trừ số tiền khỏi tài khoản người nộp.
3. Cập nhật khoản học phí → **PAID**.
4. Lưu giao dịch vào **lịch sử giao dịch**.
5. Gửi email xác nhận thành công cho **người nộp tiền**.
6. **Bổ sung theo yêu cầu rõ hơn:** gửi email xác nhận cho **cả nhà trường (email bộ phận thu học phí)**.
7. Kết thúc giao dịch, hiển thị kết quả cho người dùng.

### 3.5 Tính nhất quán khi đồng thời (2 case bắt buộc)
- **Case A – nhiều giao dịch trên cùng 1 tài khoản:** không để 2 giao dịch đồng thời cùng đọc 1 số dư rồi cùng trừ → **dư âm**. Kết quả: tổng trừ không vượt số dư.
- **Case B – nhiều tài khoản thanh toán cùng 1 khoản học phí:** chỉ **1 giao dịch thành công**, các giao dịch còn lại bị từ chối.
- Sau khi hoàn tất: số dư, trạng thái học phí, lịch sử giao dịch **phản ánh đúng kết quả cuối cùng**.

### 3.6 FSM giao dịch & job quét tự hủy
- FSM (đề xuất bổ sung trạng thái để đủ luồng OTP):

```
Start ──► PENDING ──► OTP_SENT ──► PROCESSING ──► SUCCESS ──► END
  │          │             │              │
  │          ▼             ▼              ▼
  └────► CANCELLED / EXPIRED / FAILED ────► END
```

- Trong thời gian giao dịch ở `PENDING`/`OTP_SENT`, **không cho người dùng tạo thêm giao dịch mới** cho cùng khoản học phí.
- **Job quét định kỳ 5–10s/lần**: tự hủy giao dịch không đạt ràng buộc — OTP hết hạn, giao dịch quá 5 phút, hoặc kẹt quá lâu ở trạng thái trung gian.
- Chỉ trừ tiền khi: OTP còn hạn **và** giao dịch còn `PENDING/OTP_SENT` hợp lệ.

## 4. Business Rules (danh sách ràng buộc chuẩn hóa)

| ID | Rule |
|---|---|
| BR-01 | Username phải khớp chuẩn MSSV TDTU khi đăng nhập; sai format trả lỗi 400. |
| BR-02 | Password hash lưu bảng riêng `user_credentials`, liên kết `users` qua `uid`. |
| BR-03 | Chỉ user có `uid` hợp lệ trong JWT mới gọi được API bảo vệ. |
| BR-04 | Payer/Tuition luôn được lấy từ `uid` trong JWT (`/payers/me`, `/tuition/me`), không nhận id từ client. |
| BR-05 | Chỉ thanh toán toàn bộ khoản học phí còn nợ; không thanh toán một phần. |
| BR-06 | Giao dịch chỉ được tạo khi: khoản học phí tồn tại, `UNPAID`, và `số dư ≥ số tiền`. |
| BR-07 | Một user chỉ có tối đa 1 giao dịch đang chờ (PENDING/OTP_SENT) cho cùng 1 khoản học phí. |
| BR-08 | OTP: 6 chữ số, < 5 phút, gắn 1 uid và 1 payment, không trùng OTP ACTIVE khác, chỉ dùng 1 lần; bản ghi giữ status đến khi tác vụ dọn dữ liệu xóa. |
| BR-09 | Verify OTP sai quá N lần (5) → giao dịch FAILED/CANCELLED, phải tạo giao dịch mới. |
| BR-10 | Trừ tiền = thao tác nguyên tử trên bảng account, có lock; không bao giờ để số dư âm. |
| BR-11 | Khoản học phí chỉ được thanh toán thành công đúng 1 lần (1 payment SUCCESS duy nhất). |
| BR-12 | Mọi thay đổi trạng thái payment phải đi qua FSM hợp lệ, không nhảy trạng thái tùy ý. |
| BR-13 | Job quét 5–10s: tự hủy giao dịch khi OTP hết hạn / quá 5 phút / kẹt trạng thái. |
| BR-14 | Giao dịch thành công phải gửi email cho người nộp + nhà trường. |
| BR-15 | Lịch sử giao dịch của user hiển thị đúng trạng thái cuối cùng sau mọi tình huống. |
| BR-16 | Logout chỉ vô hiệu JWT phía client/gateway (bài toán trung tâm, mức môn học: xóa token client + blacklist tùy chọn). |

## 5. Yêu cầu phi chức năng

| ID | Yêu cầu |
|---|---|
| NFR-01 | Mỗi service có **database riêng**, không truy cập chéo DB; giao tiếp chỉ qua **REST** (có thể thêm event/async ở chỗ phù hợp). |
| NFR-02 | API trả chuẩn **HTTP status code**; lỗi có body JSON thống nhất `{error: {code, message, detail}}`. |
| NFR-03 | JWT HS256, thời hạn ngắn (đề xuất 30 phút); service-to-service dùng token nội bộ. |
| NFR-04 | Idempotency cho `POST /payments` (tránh giao dịch kép khi client retry). |
| NFR-05 | Log đủ để trace một payment xuyên suốt các service (dùng `payment_id` làm correlation id). |
| NFR-06 | Mọi endpoint bảo vệ phải xác thực; lỗi 401 khi thiếu/sai token, 403 khi sai quyền. |

## 6. Các quyết định thiết kế đã chốt

1. **Self-payment only** — user chỉ trả học phí của chính mình (Project-Specific Decision).
2. **OTP quản lý dưới DB, giữ status vòng đời** — `uid` và `payment_id` mỗi khóa một OTP `ACTIVE`; hết hạn/đã dùng/hủy/resend chuyển sang status terminal, chỉ tác vụ dọn dữ liệu mới xóa.
3. **SQL Server** cho mọi database riêng — dùng `TRANSACTION`, `UPDLOCK`/row lock cho concurrency.
4. **Email thật qua Gmail SMTP** (App Password); nội dung mail OTP và mail xác nhận được tùy biến lại cho phù hợp.
5. **Job quét 5–10s** trong payment-service (background task) tự hủy giao dịch quá hạn.
6. **API Gateway** là điểm vào duy nhất của frontend; các service không expose trực tiếp ra ngoài.

## 7. Ranh giới (Out of Scope) cho bản giữa kỳ

- Đăng ký tài khoản, quên mật khẩu, nạp tiền, chuyển khoản.
- Thanh toán một phần, thanh toán hộ sinh viên khác, nhiều trường.
- Tích hợp ngân hàng thật; email nội bộ thật của TDTU.
- Refresh token, SSO, 2FA ngoài OTP.
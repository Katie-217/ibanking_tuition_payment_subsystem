# 10 — Quy định mã phản hồi (HTTP status + mã lỗi) & trạng thái nghiệp vụ

> Tài liệu này là **nguồn duy nhất** định nghĩa mọi mã mà backend trả về. Mục đích: bất kỳ ai
> (viết backend, frontend, test) nhìn mã là biết ngay chuyện gì đang xảy ra và phải xử lý sao.
> Backend **bắt buộc** sinh lỗi qua factory trong `services/shared/errors.py` — không tự bịa mã.

---

## 1. Cấu trúc trả về thống nhất

**Thành công**: trả thẳng dữ liệu JSON (không bọc envelope), ví dụ `{"payment_id": 42, ...}`.

**Lỗi**: luôn đúng 1 envelope:

```json
{
  "error": {
    "code": "INSUFFICIENT_BALANCE",
    "message": "Số dư khả dụng không đủ để thanh toán",
    "detail": "required=7000000, available=1200000"
  }
}
```

| Trường | Bắt buộc | Ý nghĩa |
|---|---|---|
| `error.code` | ✅ | Mã lỗi MÁY ĐỌC ĐƯỢC (frontend `e.code` để rẽ nhánh xử lý) |
| `error.message` | ✅ | Thông báo tiếng Việt hiển thị cho người dùng |
| `error.detail` | tùy chọn | Chi tiết kỹ thuật (field nào sai, required vs available…) |

---

## 2. Bảng HTTP Status Code

| HTTP | Tên | Dùng khi nào |
|---|---|---|
| **200** | OK | Đọc/ xử lý thành công (login, verify OTP, hủy, resend, history…) |
| **201** | Created | Tạo mới thành công (`POST /payments`) |
| **400** | Bad Request | Input sai format/validation: MSSV sai chuẩn, OTP sai định dạng, query sai kiểu |
| **401** | Unauthorized | Thiếu/ sai/ hết hạn JWT, hoặc đăng nhập sai thông tin |
| **403** | Forbidden | Đã đăng nhập nhưng **không có quyền** với tài nguyên (payment/tuition của người khác, thiếu X-Internal-Token) |
| **404** | Not Found | Không tồn tại đối tượng (payment_id, tuition_id, hồ sơ payer/student) |
| **409** | Conflict | Xung đột **trạng thái**: không đúng FSM, đã có giao dịch active, khoản đã thanh toán, bị khóa |
| **410** | Gone | (Dự phòng) tài nguyên đã bị xóa hết hạn — dự án dùng 409 + code thay cho 410 |
| **422** | Unprocessable Entity | Dữ liệu hợp lệ về mặt cú pháp nhưng **vi phạm rule nghiệp vụ**: số dư không đủ |
| **429** | Too Many Requests | Vượt giới hạn tần suất (resend OTP < 30s) |
| **500** | Internal Server Error | Lỗi hệ thống không lường trước (database lỗi…) — không lộ chi tiết cho user |
| **503** | Service Unavailable | Service phụ thuộc chưa chạy / DB không kết nối được |

---

## 3. Bảng mã lỗi nghiệp vụ (`error.code`)

> Cột "Factory" = tên hàm tương ứng trong `services/shared/errors.py` — backend gọi hàm này,
> không tự tạo `AppError` với code tự chế.

| HTTP | `code` trong body | Ý nghĩa | Factory |
|---|---|---|---|
| 400 | `VALIDATION_ERROR` | Sai format đầu vào (MSSV, OTP, page/size…) | `validation_error()` |
| 400 | `OTP_INVALID` | OTP sai, hoặc không tồn tại (đã bị xóa do dùng rồi/hết hạn) | *(otp-service)* |
| 400 | `OTP_EXPIRED` | OTP hết hạn — bản ghi đã bị xóa theo policy BR-08 | *(otp-service)* |
| 400 | `OTP_LOCKED` | Nhập sai đủ 5 lần — OTP giữ trạng thái `LOCKED`, giao dịch bị hủy và tuition được mở khóa; chỉ hoàn tiền nếu payment đã có CAPTURE | *(otp-service)* |
| 401 | `AUTH_REQUIRED` | Thiếu/ sai JWT hoặc JWT hết hạn | `auth_required()` |
| 401 | `AUTH_INVALID_CREDENTIALS` | Sai username hoặc password (thông báo chung, không tiết lộ trường sai) | `invalid_credentials()` |
| 403 | `FORBIDDEN` | Không phải chủ sở hữu / thiếu X-Internal-Token | `forbidden()` |
| 404 | `NOT_FOUND` | Không tìm thấy payment/ tuition/ hồ sơ | `not_found()` |
| 409 | `TUITION_ALREADY_PAID` | Khoản học phí đã thanh toán rồi (BR-11) | *(payment-service)* |
| 409 | `PAYMENT_ALREADY_ACTIVE` | Đã có giao dịch đang chờ cho khoản này (BR-07) | *(payment-service)* |
| 409 | `PAYMENT_EXPIRED` | Giao dịch đã bị job quét hủy do hết hạn (FR-08) | *(payment-service)* |
| 409 | `PAYMENT_CONFLICT_CONCURRENT` | Khoản học phí vừa được giao dịch khác thanh toán (đua điều kiện) | *(payment-service)* |
| 409 | `STATE_CONFLICT` | Thao tác không hợp lệ với trạng thái hiện tại của giao dịch (sai FSM) | `state_conflict()` |
| 422 | `INSUFFICIENT_BALANCE` | Số dư khả dụng không đủ; detail `required=X, available=Y` | `insufficient_balance()` |
| 422 | `BUSINESS_RULE_VIOLATION` | Vi phạm rule nghiệp vụ tổng quát khác (BR-06, BR-05…) | *(tự chọn message)* |
| 429 | `RATE_LIMITED` | Quá tần suất cho phép (resend OTP < 30s) | *(payment-service)* |
| 500 | `INTERNAL_ERROR` | Lỗi hệ thống (DB, exception chưa bắt) | handler `pyodbc.Error` |
| 503 | `SERVICE_UNAVAILABLE` | Service/ DB phụ thuộc không khả dụng (health-check fail) | `service_unavailable()` |

> `OTP_USED` **không còn dùng**: theo policy BR-08, OTP xác thực xong bị **XÓA ngay**, nên "đã
> dùng" sẽ rơi vào `OTP_INVALID` (không tìm thấy bản ghi). Không viết code sinh `OTP_USED` mới.

---

## 4. Ánh xạ mã lỗi → cách hiển thị trên UI

Frontend bắt lỗi từ `error.code` (không phụ thuộc nội dung message):

| `e.code` | Cách frontend xử lý |
|---|---|
| `AUTH_REQUIRED` | ApiClient **tự** xóa token + về trang login (không cần code thêm) |
| `AUTH_INVALID_CREDENTIALS` | Hiện "Sai mã số sinh viên hoặc mật khẩu" ở form login |
| `VALIDATION_ERROR` | Hiện lỗi ngay dưới ô nhập sai |
| `INSUFFICIENT_BALANCE` | Sau khi xác thực OTP, hiển thị "Số dư không đủ, giao dịch đã hủy — cần nạp thêm …" và yêu cầu tạo giao dịch mới; parse `detail` nếu muốn số cụ thể |
| `OTP_INVALID` / `OTP_LOCKED` | Còn N lần / đã khóa: báo theo trường hợp (FR-04) |
| `OTP_EXPIRED` | Ẩn ô nhập, hiện nút [Gửi lại mã] (FR-05) |
| `PAYMENT_ALREADY_ACTIVE` | Điều hướng sang màn hình OTP của giao dịch đang chờ đó |
| `STATE_CONFLICT` / `PAYMENT_EXPIRED` | "Giao dịch không còn hiệu lực" + làm mới dashboard |
| `SERVICE_UNAVAILABLE` | Toast "Máy chủ đang bận, thử lại sau" + giữ dữ liệu người dùng đã nhập |

---

## 5. Trạng thái nghiệp vụ (enum lưu trong DB)

### 5.1 Payment status (PaymentDB.payments)

| Status | Ý nghĩa | Badge màu UI |
|---|---|---|
| `PENDING` | Vừa tạo, đang khóa tuition (chưa gửi OTP) | xám |
| `OTP_SENT` | Đã gửi OTP, chờ nhập mã | vàng |
| `PROCESSING` | OTP đúng, đang chốt thanh toán (tuition→PAID) | xanh dương |
| `SUCCESS` | Thanh toán thành công | xanh lá |
| `FAILED` | Thất bại (hụt dư, OTP khóa, lỗi hệ thống) — đã bù trừ | đỏ |
| `CANCELLED` | User chủ động hủy — đã bù trừ | xám đậm |
| `EXPIRED` | Hết hạn, job quét tự hủy — đã bù trừ | tím nhạt |

### 5.2 Tuition status (TuitionDB.tuitions)

| Status | Ý nghĩa |
|---|---|
| `UNPAID` | Chưa nộp — hiện nút [Thanh toán] |
| `PAYING` | Đang có giao dịch xử lý (đã khóa) — chặn tạo giao dịch mới |
| `PAID` | Đã nộp xong — hiện ngày nộp |

### 5.3 User status (AuthDB.users)

| Status | Ý nghĩa |
|---|---|
| `ACTIVE` | Đăng nhập bình thường |
| `LOCKED` | Bị khóa — login báo 403 `FORBIDDEN` |

---

## 6. Quy tắc bắt buộc khi viết code

1. **Không tự bịa mã lỗi.** Chỉ dùng các mã ở mục 3. Cần mã mới → cập nhật tài liệu này +
   [docs/03](03-thiet-ke-rest-api.md) + `shared/errors.py` **cùng một PR**.
2. Error luôn theo envelope mục 1; `message` viết **tiếng Việt, dễ hiểu cho sinh viên**, không
   để lộ SQL/chuỗi lỗi nội bộ (lỗi kỹ thuật bỏ vào `detail` hoặc log server).
3. Trạng thái giao dịch chỉ đổi qua FSM (BR-12) — xem [docs/06-concurrency-fsm.md](06-concurrency-fsm.md);
   không được UPDATE `status` tùy tiện ngoài các bước đã thiết kế.
4. Test (`scripts/test_api.py`, Swagger) phải kiểm tra đúng các mã trong bảng — một endpoint
   "chạy được" nghĩa là trả **đúng mã** cho từng nhánh lỗi, không chỉ nhánh thành công.
# FR-04 — Xác thực OTP & hoàn tất thanh toán

| Mục | Nội dung |
|---|---|
| Mã chức năng | FR-04 |
| Nhánh làm việc | `feature/fr04-xac-thuc-otp` |
| Service liên quan | payment-service (orchestrator) + otp, tuition, payer, notification |
| Màn hình frontend | màn hình nhập OTP (từ FR-03) → màn hình kết quả giao dịch |
| Tài liệu tham chiếu | BR-08→BR-12, BR-14 · docs/03 mục 2.7 · docs/05 luồng "Xác thực OTP" · docs/06 FSM + Case A |

---

## 1. Chức năng là gì

User nhập mã OTP 6 số đã nhận qua email. Nếu đúng, hệ thống mới bắt đầu xử lý thanh toán:
chuyển payment sang `PROCESSING`, capture số dư, sau đó học phí mới chuyển `PAID` và giao dịch
mới chuyển `SUCCESS`. Gửi email xác nhận cho **sinh viên + nhà trường** sau khi thành công.
Nếu capture thất bại do thiếu tiền, giao dịch `FAILED`, mở khóa học phí và người dùng phải tạo
giao dịch mới sau khi nạp tiền. Nếu sai quá số lần (5), giao dịch `FAILED` và mở khóa học phí.

## 2. Flow hoạt động

```
1. User nhập 6 số → POST /payments/{id}/verify-otp {otp}
2. payment-service:
   a. Load payment, kiểm tra thuộc uid (403 nếu không phải chủ) + status = OTP_SENT (409 nếu sai FSM)
   b. POST /internal/otp/verify {payment_id, code} → otp-service:
      - Không tìm thấy OTP → trả OTP_INVALID
      - Hết hạn: cập nhật status=EXPIRED, trả OTP_EXPIRED
      - Sai: giữ status=ACTIVE, tăng attempts và ghi status_reason=INVALID_CODE; đủ 5 lần → status=LOCKED, trả OTP_LOCKED
      - Đúng: cập nhật status=USED, trả verified (BR-08: mã chỉ dùng đúng 1 lần)
  c. OTP sai → trả lỗi, payment vẫn OTP_SENT; OTP hết hạn → OTP chuyển EXPIRED, payment vẫn OTP_SENT nếu payment chưa hết hạn để có thể resend; OTP_LOCKED → xử lý như hủy (bước g)
  d. Đúng → payment OTP_SENT → PROCESSING → gọi POST /internal/balance/capture
    (trừ nguyên tử; 422 nếu số dư không đủ)
  e. Nếu capture thiếu tiền: release tuition (PAYING→UNPAID), payment FAILED,
    reason=INSUFFICIENT_BALANCE; không release balance vì chưa có CAPTURE
  f. Nếu capture thành công: gọi POST /internal/tuitions/{id}/paid
    (PAYING→PAID, lưu paid_by_payment_id; unique index ux_payments_success chặn 2 lần SUCCESS)
  g. payment → SUCCESS, lưu completed_at, ghi payment_history
  h. Gửi email xác nhận cho sinh viên + copy nhà trường (POST /internal/notifications/confirm-email)
      — gửi bất đồng bộ, lỗi email KHÔNG làm payment fail (đã SUCCESS rồi)
3. Trả receipt cho frontend → hiển thị màn hình giao dịch thành công
```

**Nhánh lỗi OTP_LOCKED** (sai đủ 5 lần): release tuition (`PAYING→UNPAID`), payment → FAILED,
ghi lý do `OTP_LOCKED`; không release balance vì giao dịch chưa capture; OTP giữ status `LOCKED`.

## 3. API cần dùng

| Method | Endpoint | Ý nghĩa trong chức năng này |
|---|---|---|
| POST | `/payments/{id}/verify-otp` | Xác thực OTP — điểm vào duy nhất |
| POST | `/internal/otp/verify` | Kiểm tra mã, đếm lượt sai và cập nhật status OTP |
| POST | `/internal/tuitions/{id}/paid` | Đánh dấu học phí đã nộp PAYING→PAID |
| POST | `/internal/notifications/confirm-email` | Gửi email xác nhận sinh viên + nhà trường |
| POST | `/internal/tuitions/{id}/release` | Bù trừ khi OTP_LOCKED |
| POST | `/internal/balance/release` | Chỉ hoàn tiền khi payment đã có CAPTURE; không gọi cho OTP_LOCKED trước capture |

## 4. Frontend — UI cần build

1. **Ô nhập OTP**: 1 ô nhập 6 chữ số (hoặc 6 ô con tự nhảy focus), auto-submit khi đủ 6 số.
   Đồng hồ đếm ngược từ 300s; về 0 → thông báo "Mã đã hết hạn" + hiện nút **[Gửi lại mã]** (FR-05).
2. **Thông báo lỗi theo code**:
   | code | Hiển thị trên UI |
   |---|---|
   | `OTP_INVALID` | "Mã OTP không đúng, còn N lần thử" |
  | `OTP_EXPIRED` | "Mã OTP đã hết hạn" (ẩn ô nhập, bật nút gửi lại cùng giao dịch) |
  | `OTP_LOCKED` | "Nhập sai quá 5 lần — giao dịch đã hủy, học phí đã mở khóa" → nút về trang chính |
  | `INSUFFICIENT_BALANCE` | "Số dư không đủ, giao dịch đã hủy; vui lòng nạp tiền và thực hiện lại" → nút về trang chính |
   | `STATE_CONFLICT` | "Giao dịch không còn hiệu lực" |
3. **Màn hình kết quả thành công**: biểu tượng ✓, "Thanh toán thành công", mã giao dịch,
   số tiền, ngày giờ, nút **[Về trang chính]** (dashboard tự làm mới số dư + danh sách học phí).

## 5. Logic backend

- OTP xác thực **đúng 1 lần**: verify thành công cập nhật status `USED` (BR-08) — gọi lại
  lần 2 sẽ báo `OTP_INVALID`, đồng thời payment đã SUCCESS cũng chặn bởi FSM (409).
- Thứ tự đảm bảo nhất quán: xác thực OTP → PROCESSING → capture balance → đổi tuition PAID
  → payment SUCCESS. Nếu capture thất bại thì không trừ tiền; nếu tuition đổi trạng thái lỗi
  sau capture thì phải release balance bằng ledger và release tuition theo đúng payment_id.
- `ux_payments_success(tuition_id)` ở PaymentDB là **rào chắn cuối**: dù 2 request SUCCESS chạy
  song song, DB chỉ cho 1 dòng tồn tại (BR-11).
- Email xác nhận: gửi cho sinh viên + `cc` email nhà trường (`schools.finance_email`); lỗi
  gửi mail chỉ ghi log/retry ở notification-service, không đảo ngược payment (BR-14).

## 6. Ràng buộc

| Ràng buộc | Giải thích |
|---|---|
| BR-08 | OTP 6 số, < 5 phút, 1 uid/1 payment có 1 mã ACTIVE, dùng 1 lần; status được giữ lại |
| BR-09 | Sai đủ 5 lần → giao dịch FAILED + mở khóa tuition; vì chưa capture nên không hoàn tiền |
| BR-10 | Hoàn tiền (release) chỉ cộng lại đúng 1 lần cho 1 payment_id |
| BR-11 | 1 khoản học phí chỉ 1 lần SUCCESS, kể cả khi 2 tab cùng bấm |
| BR-12 | FSM: OTP_SENT→PROCESSING→SUCCESS; verify trên payment FAILED/SUCCESS → 409 |
| BR-14 | Thành công phải gửi email cho người nộp + nhà trường |

## 7. Output mong đợi

Thành công (200):

```json
{
  "payment_id": 42,
  "status": "SUCCESS",
  "amount": 7000000,
  "student": {"student_id": "521H0092", "full_name": "Nguyễn Văn A"},
  "tuition_id": 10,
  "balance_after": 8000000,
  "completed_at": "2026-08-31T10:32:15Z"
}
```

Sau khi gọi: số dư đã capture, tuition = `PAID` + `paid_at` + `paid_by_payment_id=42`;
payment = `SUCCESS`; bản ghi OTP giữ status `USED`; hộp thư sinh viên + trường có email xác nhận.

**Định nghĩa hoàn thành (Done):** nhập đúng → SUCCESS + 2 email; nhập sai → thông báo sai và
đếm lần; sai đủ 5 lần → hủy + mở khóa, không hoàn tiền vì chưa capture; gọi verify 2 lần cùng mã → lần 2 báo
`OTP_INVALID`; verify trên payment đã SUCCESS → 409.

## 8. Mã response

| HTTP | code | Ý nghĩa / khi nào xảy ra |
|---|---|---|
| 200 | — | Xác thực thành công, payment SUCCESS |
| 400 | `VALIDATION_ERROR` | Mã OTP sai format (không đủ 6 chữ số) |
| 400 | `OTP_INVALID` | OTP sai hoặc OTP terminal không còn hiệu lực |
| 400 | `OTP_EXPIRED` | OTP hết hạn — bản ghi giữ status `EXPIRED`, có thể resend nếu payment còn hiệu lực |
| 400 | `OTP_LOCKED` | Sai đủ 5 lần — giao dịch đã bị hủy và tuition đã mở khóa; chưa có tiền để hoàn |
| 401 | `AUTH_REQUIRED` | Thiếu JWT |
| 403 | `FORBIDDEN` | Payment không thuộc uid |
| 404 | `NOT_FOUND` | Không tìm thấy payment |
| 409 | `STATE_CONFLICT` | Payment không ở trạng thái OTP_SENT (sai FSM) |
| 409 | `PAYMENT_CONFLICT_CONCURRENT` | Khoản học phí vừa được giao dịch khác thanh toán xong |
| 422 | `BUSINESS_RULE_VIOLATION` | Vi phạm rule khác (vd số dư biến động khi đang xử lý) |
| 500 | `INTERNAL_ERROR` | Lỗi hệ thống |
| 503 | `SERVICE_UNAVAILABLE` | otp/tuition/notification service không khả dụng |

## 9. Nhánh Git & quy trình

Làm toàn bộ chức năng trên nhánh **`feature/fr04-xac-thuc-otp`** — tuân thủ
[docs/fr/00-quy-trinh-git.md](00-quy-trinh-git.md): quét lại dự án + kiểm tra remote + pull main
trước khi code → giải quyết xong conflict mới push → mở PR kèm mô tả đã làm → chờ duyệt.
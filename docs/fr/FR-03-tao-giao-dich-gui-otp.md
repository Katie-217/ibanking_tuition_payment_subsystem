# FR-03 — Tạo giao dịch thanh toán & gửi OTP

| Mục | Nội dung |
|---|---|
| Mã chức năng | FR-03 |
| Nhánh làm việc | `feature/fr03-tao-giao-dich-gui-otp` |
| Service liên quan | payment-service (orchestrator) + payer, tuition, otp, notification |
| Màn hình frontend | modal xác nhận trong `dashboard.html` → màn hình nhập OTP |
| Tài liệu tham chiếu | BR-05→BR-08, BR-10 · docs/03 mục 2.6 · docs/05 luồng "Tạo giao dịch + OTP" · docs/06 FSM |

---

## 1. Chức năng là gì

Từ một khoản học phí `UNPAID`, user bấm **[Thanh toán]** để tạo **giao dịch**:
hệ thống khóa khoản học phí, sinh **OTP 6 số gửi qua email** và chuyển sang bước xác thực
(FR-04). Ở bước này **chưa trừ tiền**; số dư có thể thay đổi trước khi user nhập OTP.
Chỉ khi OTP đúng hệ thống mới capture tiền. Nếu đến cuối không thanh toán được, mọi thay đổi
được bù trừ — không để lại trạng thái dở.

## 2. Flow hoạt động

```
1. User chọn khoản UNPAID → modal xác nhận: học kỳ, số tiền, số dư hiện tại
2. Bấm [Xác nhận & nhận OTP] → POST /payments {tuition_id} + header Idempotency-Key
3. payment-service (orchestrator) thực hiện theo thứ tự:
   a. Kiểm tra Idempotency-Key: đã có payment trùng key → trả lại payment đó (không tạo mới)
   b. GET  /internal/tuitions/{id}         → xác nhận tồn tại, thuộc uid, amount
   c. POST /internal/tuitions/{id}/lock    → UNPAID→PAYING (conditional UPDATE, chống double-pay)
   d. Tạo bản ghi payment status = PENDING
      (vướng UNIQUE ux_payments_active(uid) → trả 409 PAYMENT_ALREADY_ACTIVE, dừng;
      cùng một tài khoản không được có payment đang chờ ở khoản học phí khác)
   e. POST /internal/otp/generate {payment_id, uid, email} → OTP 6 số, 5 phút (chuyển OTP ACTIVE cũ sang REPLACED)
   f. POST /internal/notifications/otp-email → gửi mail chứa OTP
   g. payment → OTP_SENT, ghi lịch sử, trả {payment_id, ...}
4. Frontend chuyển sang màn hình nhập OTP với đồng hồ đếm ngược 5 phút
```

**Bù trừ (compensation)** khi lỗi giữa chừng: nếu tạo/gửi OTP thất bại → invalidate OTP,
release tuition (`PAYING→UNPAID`) + payment `FAILED`. Không gọi release balance trong FR-03
vì chưa có capture. Thông báo lỗi: "Không gửi được email, mời thử lại".

## 3. API cần dùng

| Method | Endpoint | Ý nghĩa trong chức năng này |
|---|---|---|
| POST | `/payments` | Tạo giao dịch — điểm vào duy nhất (Bearer + Idempotency-Key) |
| GET | `/internal/tuitions/{id}` | Orchestrator đọc tuition + kiểm tra chủ sở hữu |
| POST | `/internal/tuitions/{id}/lock` | Khóa khoản học phí UNPAID→PAYING |
| POST | `/internal/balance/capture` | Trừ tiền nguyên tử sau khi OTP đúng, idempotent theo payment_id |
| POST | `/internal/otp/generate` | Sinh OTP 6 số (chuyển OTP ACTIVE cũ sang REPLACED) |
| POST | `/internal/notifications/otp-email` | Gửi email chứa OTP |
| POST | `/internal/tuitions/{id}/release` | Bù trừ mở khóa khi thất bại |
| POST | `/internal/balance/release` | Bù trừ hoàn tiền nếu đã có CAPTURE; không dùng trong FR-03 |

## 4. Frontend — UI cần build

1. **Modal xác nhận thanh toán** (trên dashboard):
   - Dòng khóa học: "Học kỳ 2025-2026-HK1", "Số tiền: 7.000.000 ₫", "Số dư hiện tại: 15.000.000 ₫".
   - Nút **[Hủy]** (đóng modal) + **[Xác nhận & nhận OTP]**.
   - Khi gửi: disable nút, hiện "Đang tạo giao dịch…" — và tạo `Idempotency-Key` bằng
     `ApiClient.newIdempotencyKey()` **một lần duy nhất** cho cả lần bấm (chống double-click).
2. **Màn hình nhập OTP** (hoặc view trong modal): hiển thị "Mã OTP đã gửi về email
   `521***@student.tdtu.edu.vn`", đồng hồ đếm ngược 5:00, ô nhập 6 số, nút
   **[Xác nhận thanh toán]**, liên kết **[Gửi lại mã]** (FR-05) và nút **[Hủy giao dịch]** (FR-06).
3. **Xử lý lỗi ngay tại modal**: `409 PAYMENT_ALREADY_ACTIVE` → dẫn sang ngay giao dịch
   đang chờ (điều hướng tới màn hình OTP của payment đó).

## 5. Logic backend

- Orchestrator dùng **saga bù trừ**: mỗi bước gọi 1 service khác; bước nào fail thì gọi đúng
  "cặp bù" của các bước đã thành công (lock↔release, capture↔release) — xem docs/05.
- **Chống double-pay 2 tầng**: (1) conditional UPDATE `UNPAID→PAYING` chỉ thành công 1 lần;
   (2) filtered unique index `ux_payments_active(uid)` chặn 2 giao dịch cùng tài khoản.
- **Idempotency**: `Idempotency-Key` duy nhất trên bảng payments; retry trả lại payment cũ.
- Trừ tiền có idempotent theo `payment_id` (bảng balance_ledger) — lỡ gọi 2 lần vẫn trừ 1 lần.

## 6. Ràng buộc

| Ràng buộc | Giải thích |
|---|---|
| BR-05 | Thanh toán toàn bộ khoản nợ (amount lấy từ DB, client không truyền số tiền) |
| BR-06 | Chỉ tạo giao dịch khi tuition tồn tại + `UNPAID`; số dư tại thời điểm tạo chỉ hiển thị tham khảo, kiểm tra quyết định thực hiện lúc capture sau OTP |
| BR-07 | Mỗi uid tối đa 1 giao dịch PENDING/OTP_SENT/PROCESSING |
| BR-08 | OTP 6 số, hạn < 5 phút, 1 OTP ACTIVE gắn 1 uid và 1 payment; status được giữ lại |
| BR-10 | Trừ tiền nguyên tử, không bao giờ âm |
| BR-12 | Chuyển trạng thái đúng FSM (PENDING→OTP_SENT, không nhảy bước) |

## 7. Output mong đợi

Thành công (201):

```json
{
  "payment_id": 42,
  "status": "OTP_SENT",
  "amount": 7000000,
  "student_id": "521H0092",
  "tuition_id": 10,
  "otp_expires_in_seconds": 300,
  "created_at": "2026-08-31T10:30:00Z"
}
```

Sau khi gọi: số dư **chưa giảm**, tuition = `PAYING`, email nhận đúng mã OTP 6 số.

**Định nghĩa hoàn thành (Done):** tạo giao dịch cho uid1 thành công và email tới;
khoản đã `PAYING`/`PAID` hoặc thiếu dư đều bị chặn với mã lỗi đúng; gọi lại cùng
Idempotency-Key không tạo payment thứ 2.

## 8. Mã response

| HTTP | code | Ý nghĩa / khi nào xảy ra |
|---|---|---|
| 201 | — | Tạo giao dịch + gửi OTP thành công |
| 400 | `VALIDATION_ERROR` | Body thiếu/ sai kiểu tuition_id |
| 401 | `AUTH_REQUIRED` | Thiếu JWT |
| 403 | `FORBIDDEN` | Tuition không thuộc uid (BR-04) |
| 404 | `NOT_FOUND` | Không tìm thấy khoản học phí |
| 409 | `TUITION_ALREADY_PAID` | Khoản này đã nộp rồi |
| 409 | `PAYMENT_ALREADY_ACTIVE` | Đã có giao dịch đang chờ cho khoản này (BR-07) |
| 409 | `STATE_CONFLICT` | Trạng thái không hợp lệ (đang PAYING/khóa) |
| 422 | `INSUFFICIENT_BALANCE` | Số dư không đủ (detail: required/available) |
| 500 | `INTERNAL_ERROR` | Lỗi hệ thống |
| 503 | `SERVICE_UNAVAILABLE` | 1 service con (otp/notification/payer…) không khả dụng → đã bù trừ |

## 9. Nhánh Git & quy trình

Làm toàn bộ chức năng trên nhánh **`feature/fr03-tao-giao-dich-gui-otp`** — tuân thủ
[docs/fr/00-quy-trinh-git.md](00-quy-trinh-git.md): quét lại dự án + kiểm tra remote + pull main
trước khi code → giải quyết xong conflict mới push → mở PR kèm mô tả đã làm → chờ duyệt.
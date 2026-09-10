# FR-05 — Gửi lại OTP

| Mục | Nội dung |
|---|---|
| Mã chức năng | FR-05 |
| Nhánh làm việc | `feature/fr05-gui-lai-otp` |
| Service liên quan | payment-service + otp-service + notification-service |
| Màn hình frontend | nút [Gửi lại mã] trên màn hình nhập OTP |
| Tài liệu tham chiếu | BR-08 · docs/03 mục 2.8 · docs/05 luồng "Xác thực OTP" (nhánh resend) |

---

## 1. Chức năng là gì

Khi user chưa nhận được email OTP hoặc mã đã hết hạn, cho phép **gửi lại mã mới**: OTP cũ được
giữ lại với trạng thái terminal (`REPLACED` hoặc `EXPIRED`), hệ thống sinh **mã 6 số mới**
(không trùng bất kỳ OTP đang hiệu lực nào) và gửi email lần nữa cho cùng giao dịch — không tạo
giao dịch mới, không trừ tiền.

## 2. Flow hoạt động

```
1. User bấm [Gửi lại mã] → POST /payments/{id}/resend-otp (không cần body)
2. payment-service:
    a. Load payment, kiểm tra chủ sở hữu + status = OTP_SENT (409 nếu sai FSM). Payment vẫn có thể resend khi OTP hiện tại đã EXPIRED, miễn `payment.expires_at` chưa qua.
   b. Chống spam: mỗi payment tối đa 1 lần gửi lại trong 30 giây → vi phạm: 429
  c. POST /internal/otp/generate: otp-service chuyển OTP ACTIVE cũ sang REPLACED,
    tạo OTP mới 6 số, hạn 5 phút trong cùng transaction (BR-08)
   d. POST /internal/notifications/otp-email → gửi email với mã mới
3. Frontend reset đồng hồ đếm ngược về 5:00, xóa ô nhập cũ, thông báo "Đã gửi mã mới"
```

## 3. API cần dùng

| Method | Endpoint | Ý nghĩa trong chức năng này |
|---|---|---|
| POST | `/payments/{id}/resend-otp` | Yêu cầu gửi lại OTP |
| POST | `/internal/otp/generate` | Chuyển OTP cũ sang REPLACED + sinh OTP mới (không trùng mã ACTIVE khác) |
| POST | `/internal/notifications/otp-email` | Gửi email chứa mã mới |

## 4. Frontend — UI cần build

- Trên màn hình nhập OTP: liên kết/nút **[Gửi lại mã]** — mặc định ẩn, **chỉ hiện sau 30 giây**
  kể từ lần gửi trước (frontend đếm ngược, tránh gọi thừa dính 429).
- Khi gửi: nút thành "Đang gửi…" (disable); gửi xong → reset timer 5:00, toast "Đã gửi mã mới,
  kiểm tra email".
- Lỗi `429 RATE_LIMITED` → thông báo "Vui lòng chờ X giây nữa mới gửi lại".
- Lỗi `409 STATE_CONFLICT` → "Giao dịch không còn hiệu lực gửi lại mã".

## 5. Logic backend

- otp-service giữ bất biến **1 uid và 1 payment tối đa 1 OTP ACTIVE** bằng filtered unique index;
  `generate` chuyển OTP cũ sang `REPLACED` rồi INSERT mã mới trong cùng transaction. Bản ghi
  terminal không bị xóa trong flow nghiệp vụ.
- Mã mới không được trùng bất kỳ OTP ACTIVE khác: vòng lặp sinh lại nếu vi phạm `UNIQUE(code)`.
- Throttle 30s tính từ lần sinh OTP gần nhất của payment đó (ghi `last_resend_at`/dựa created_at).

## 6. Ràng buộc

| Ràng buộc | Giải thích |
|---|---|
| BR-08 | OTP mới vẫn: 6 số, < 5 phút, 1 uid/1 payment chỉ 1 mã ACTIVE; OTP cũ chuyển REPLACED/EXPIRED |
| BR-12 | Chỉ resend khi payment đang OTP_SENT |
| Chống spam | Tối đa 1 lần/30s mỗi payment → 429 nếu vi phạm |

## 7. Output mong đợi

Thành công (200):

```json
{"payment_id": 42, "otp_expires_in_seconds": 300}
```

Sau khi gọi: OTPDB chỉ còn đúng 1 bản ghi cho payment 42 với mã MỚI; email thứ 2 tới đúng hộp thư.

**Định nghĩa hoàn thành (Done):** resend thành công thì mã cũ không xác thực được nữa, mã mới
xác thực được (FR-04); gọi resend lần nữa dưới 30s → 429; resend trên payment hủy/SUCCESS → 409.

## 8. Mã response

| HTTP | code | Ý nghĩa / khi nào xảy ra |
|---|---|---|
| 200 | — | Đã gửi mã mới |
| 401 | `AUTH_REQUIRED` | Thiếu JWT |
| 403 | `FORBIDDEN` | Payment không thuộc uid |
| 404 | `NOT_FOUND` | Không tìm thấy payment |
| 409 | `STATE_CONFLICT` | Payment không ở OTP_SENT / đã kết thúc |
| 429 | `RATE_LIMITED` | Gửi lại quá nhanh (< 30 giây) |
| 500 | `INTERNAL_ERROR` | Lỗi hệ thống |
| 503 | `SERVICE_UNAVAILABLE` | otp/notification không khả dụng |

## 9. Nhánh Git & quy trình

Làm toàn bộ chức năng trên nhánh **`feature/fr05-gui-lai-otp`** — tuân thủ
[docs/fr/00-quy-trinh-git.md](00-quy-trinh-git.md): quét lại dự án + kiểm tra remote + pull main
trước khi code → giải quyết xong conflict mới push → mở PR kèm mô tả đã làm → chờ duyệt.
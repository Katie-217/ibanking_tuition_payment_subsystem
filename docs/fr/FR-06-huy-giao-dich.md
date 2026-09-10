# FR-06 — Hủy giao dịch đang chờ

| Mục | Nội dung |
|---|---|
| Mã chức năng | FR-06 |
| Nhánh làm việc | `feature/fr06-huy-giao-dich` |
| Service liên quan | payment-service + otp, tuition, payer |
| Màn hình frontend | nút [Hủy giao dịch] trên màn hình nhập OTP |
| Tài liệu tham chiếu | BR-08, BR-12 · docs/03 mục 2.9 · docs/05 luồng "Hủy giao dịch" · docs/06 compensation |

---

## 1. Chức năng là gì

User chủ động hủy một giao dịch đang chờ xác thực OTP (PENDING/OTP_SENT). Hệ thống **dọn sạch
mọi hệ quả của giao dịch**: đánh dấu OTP `CANCELLED`, mở khóa khoản học phí (PAYING→UNPAID), **hoàn lại tiền đã
trừ**, chuyển payment sang `CANCELLED` và ghi lịch sử. Sau hủy, user có thể tạo giao dịch mới.

## 2. Flow hoạt động

```
1. User bấm [Hủy giao dịch] → confirm "Hủy giao dịch này?" → POST /payments/{id}/cancel
2. payment-service:
   a. Load payment, kiểm tra chủ sở hữu + status trong (PENDING, OTP_SENT) — 409 nếu sai FSM
      (PROCESSING/SUCCESS/FAILED/CANCELLED/EXPIRED đều KHÔNG hủy được)
  b. POST /internal/otp/invalidate → cập nhật bản ghi OTP của payment thành `CANCELLED` (BR-08)
   c. POST /internal/tuitions/{id}/release → tuition PAYING→UNPAID (nếu đang khóa)
   d. POST /internal/balance/release → hoàn tiền đã capture (idempotent theo payment_id)
   e. payment → CANCELLED, ghi payment_history
3. Frontend quay về dashboard; số dư + danh sách học phí được làm mới
```

> Thứ tự (c)-(d)-(e): dù lỗi xảy ra giữa chừng, các endpoint release đều **idempotent** nên
> payment-service có thể gọi lại an toàn cho tới khi toàn bộ về trạng thái sạch.

## 3. API cần dùng

| Method | Endpoint | Ý nghĩa trong chức năng này |
|---|---|---|
| POST | `/payments/{id}/cancel` | Hủy giao dịch đang chờ |
| POST | `/internal/otp/invalidate` | Đánh dấu OTP của payment là `CANCELLED` |
| POST | `/internal/tuitions/{id}/release` | Mở khóa học phí PAYING→UNPAID |
| POST | `/internal/balance/release` | Hoàn tiền đã trừ (không cộng 2 lần cho cùng payment_id) |

## 4. Frontend — UI cần build

- Trên màn hình nhập OTP: nút phụ **[Hủy giao dịch]** (màu xám/đỏ nhạt).
- Bấm → dialog xác nhận: "Hủy giao dịch 7.000.000 ₫ cho kỳ 2025-2026-HK1? Số dư sẽ được hoàn lại."
- Đang hủy: disable nút + "Đang hủy…"; xong → đóng màn hình OTP, toast xanh
  "Đã hủy giao dịch, số dư đã hoàn lại", dashboard tự reload số dư + danh sách học phí.
- Lỗi `409 STATE_CONFLICT` → "Giao dịch đang xử lý/đã kết thúc, không thể hủy".

## 5. Logic backend

- Điều kiện hủy kiểm ở **payment-service** (FSM — BR-12): chỉ PENDING/OTP_SENT được hủy;
  đang PROCESSING (đã qua verify OTP) không hủy để tránh mất đồng bộ với bước trừ tiền/đổi PAID.
- Các bước bù trừ đều chạy an toàn khi lặp: tuition release nếu đang PAYING; balance release
  chỉ cộng 1 lần nhờ `UNIQUE(payment_id, change_type)` trên balance_ledger.
- Đánh dấu OTP `CANCELLED` ngay cả khi payment chưa OTP_SENT (trường hợp hủy lúc PENDING, có thể chưa có OTP)
  — otp-service không có bản ghi thì trả OK như nhau (idempotent).

## 6. Ràng buộc

| Ràng buộc | Giải thích |
|---|---|
| BR-08 | OTP của giao dịch bị XÓA ngay khi hủy — không tồn tại mã mồ côi |
| BR-10 | Hoàn tiền đúng 1 lần/1 payment_id; số dư về đúng giá trị trước giao dịch |
| BR-12 | Chỉ hủy hợp lệ từ PENDING/OTP_SENT (FSM); SUCCESS/FAILED/CANCELLED/EXPIRED → 409 |
| BR-07 | Sau hủy, unique index active giải phóng → user được tạo giao dịch mới cho cùng khoản |

## 7. Output mong đợi

Thành công (200):

```json
{"payment_id": 42, "status": "CANCELLED"}
```

Sau khi gọi: số dư uid1 về đúng 15.000.000; tuition về `UNPAID`; OTPDB sạch bản ghi payment 42;
`GET /payments/42` trả status `CANCELLED`.

**Định nghĩa hoàn thành (Done):** hủy xong toàn bộ trạng thái về như trước giao dịch; hủy lần 2
→ 409; hủy giao dịch đã SUCCESS → 409; người khác không hủy được (403).

## 8. Mã response

| HTTP | code | Ý nghĩa / khi nào xảy ra |
|---|---|---|
| 200 | — | Hủy thành công, đã bù trừ đầy đủ |
| 401 | `AUTH_REQUIRED` | Thiếu JWT |
| 403 | `FORBIDDEN` | Payment không thuộc uid |
| 404 | `NOT_FOUND` | Không tìm thấy payment |
| 409 | `STATE_CONFLICT` | Payment không ở trạng thái hủy được |
| 500 | `INTERNAL_ERROR` | Lỗi hệ thống |
| 503 | `SERVICE_UNAVAILABLE` | otp/tuition/payer không khả dụng (bù trừ sẽ retry) |

## 9. Nhánh Git & quy trình

Làm toàn bộ chức năng trên nhánh **`feature/fr06-huy-giao-dich`** — tuân thủ
[docs/fr/00-quy-trinh-git.md](00-quy-trinh-git.md): quét lại dự án + kiểm tra remote + pull main
trước khi code → giải quyết xong conflict mới push → mở PR kèm mô tả đã làm → chờ duyệt.
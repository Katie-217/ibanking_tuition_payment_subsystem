# FR-08 — Job quét giao dịch hết hạn (sweep job)

| Mục | Nội dung |
|---|---|
| Mã chức năng | FR-08 |
| Nhánh làm việc | `feature/fr08-job-quet-het-han` |
| Service liên quan | payment-service (background task) + otp, tuition, payer |
| Màn hình frontend | **không có UI** — chạy nền; UI chỉ thấy kết quả qua lịch sử (FR-07) |
| Tài liệu tham chiếu | BR-08, BR-13, BR-15 · docs/05 luồng "Job quét" · docs/06 sweep job spec |

---

## 1. Chức năng là gì

Một tiến trình nền trong payment-service, định kỳ **5–10 giây** quét OTP hết hạn và các payment
đã quá thời hạn. OTP hết hạn **không tự kết thúc payment ngay**: OTP chuyển `EXPIRED`, payment
vẫn `OTP_SENT` để user có thể resend nếu `payment.expires_at` chưa qua. Khi payment thực sự quá
hạn, job tự động kết thúc giao dịch: vô hiệu OTP, mở khóa học phí, chỉ hoàn tiền nếu ledger đã
có CAPTURE, chuyển payment sang `EXPIRED` và ghi lịch sử —
đảm bảo không giao dịch nào treo vô hạn, tài nguyên được giải phóng (BR-13, BR-15).

## 2. Flow hoạt động

```
1. Loop nền trong payment-service, ngủ 5–10 giây giữa các lần quét
2. Mỗi chu kỳ quét:
  a. UPDATE otps SET status='EXPIRED' WHERE status='ACTIVE' AND expires_at <= now
  b. SELECT ... FROM payments
    WHERE status IN ('PENDING','OTP_SENT','PROCESSING') AND expires_at <= SYSUTCDATETIME()
   (lấy theo đợt — ví dụ 100 dòng/lần, để không quét lại vô hạn nếu có lỗi)
3. Với từng payment hết hạn:
  a. POST /internal/otp/invalidate          → cập nhật OTP còn ACTIVE thành CANCELLED/EXPIRED
  b. POST /internal/tuitions/{id}/release   → tuition PAYING→UNPAID, có ràng buộc payment_id
  c. POST /internal/balance/release         → chỉ hoàn nếu ledger đã có CAPTURE
  d. payment → EXPIRED, ghi payment_history (note: "Hết hạn — job quét hủy")
4. Nếu 1 payment lỗi giữa chừng → ghi log, bỏ qua, chu kỳ sau quét lại
   (các bước release idempotent nên chạy lặp an toàn)
```

## 3. API cần dùng (gọi từ job)

| Method | Endpoint | Ý nghĩa trong chức năng này |
|---|---|---|
| POST | `/internal/otp/invalidate` | Cập nhật OTP còn hiệu lực của payment hết hạn thành `EXPIRED` |
| POST | `/internal/tuitions/{id}/release` | Trả khoản học phí về UNPAID |
| POST | `/internal/balance/release` | Hoàn tiền sinh viên (idempotent) |

Không có API công khai — job chỉ chạy trong payment-service.

## 4. Frontend — UI cần build

Không có UI riêng. Hiệu ứng người dùng nhìn thấy:

- Màn hình nhập OTP qua `payment.expires_at` không bấm → lần gọi tiếp theo nhận 409/`PAYMENT_EXPIRED`;
  frontend hiện "Giao dịch đã hết hạn, học phí đã được mở khóa". Số dư chỉ được hoàn nếu giao dịch
  đã capture trước đó.
- Trang lịch sử (FR-07) xuất hiện dòng trạng thái **`EXPIRED`** — bằng chứng job đã chạy.

## 5. Logic backend

- Chạy bằng vòng lặp `asyncio`/thread trong payment-service, khởi động cùng ứng dụng
  (FastAPI startup event `@app.on_event("startup")` hoặc lifespan).
- Vòng lặp **bọc try/except** toàn cục: 1 giao dịch lỗi không làm chết job; luôn `sleep 5-10s`
  giữa các chu kỳ kể cả khi có exception.
- Ghi log từng payment xử lý (payment_id, kết quả, lý do) — phục vụ demo & debug.
- Điều kiện đổi trạng thái vẫn đi qua FSM: chỉ PENDING/OTP_SENT → EXPIRED (BR-12).

## 6. Ràng buộc

| Ràng buộc | Giải thích |
|---|---|
| BR-08 | OTP hết hạn chuyển `EXPIRED`; bản ghi được giữ để audit, có thể dọn bằng job retention riêng |
| BR-13 | Chu kỳ quét 5–10 giây; kết thúc payment khi `payment.expires_at` hết hạn hoặc giao dịch bị kẹt |
| BR-10 | Hoàn tiền đúng 1 lần cho mỗi payment_id |
| BR-15 | Lịch sử ghi nhận `EXPIRED` — user biết giao dịch đã kết thúc và tuition đã được mở khóa |
| BR-07 | Sau khi hủy, unique index active được giải phóng → tạo giao dịch mới được |

## 7. Output mong đợi

Không trả JSON cho ai; kết quả kiểm chứng qua database:

```sql
-- payment quá hạn chuyển EXPIRED, tuition trở về UNPAID, balance hoàn đủ
SELECT payment_id, status, expires_at FROM PaymentDB.dbo.payments WHERE status = 'EXPIRED';
SELECT tuition_id, status FROM TuitionDB.dbo.tuitions WHERE student_id = '521H0092';
SELECT payment_id, status FROM OTPDB.dbo.otps WHERE payment_id = 42; -- bản ghi terminal để audit
```

**Định nghĩa hoàn thành (Done):** OTP hết hạn thì chuyển `EXPIRED` và có thể resend nếu payment
còn hiệu lực; khi payment quá hạn, trong khoảng 5–10 giây giao dịch tự chuyển `EXPIRED`, tuition
về `UNPAID`, số dư chỉ hoàn đúng nếu đã capture, OTP giữ trạng thái terminal;
lịch sử hiện trạng thái EXPIRED; không có giao dịch PENDING/OTP_SENT nào sống quá `expires_at` + 10 giây.

## 8. Mã response (khi user thao tác trên giao dịch đã hết hạn)

| HTTP | code | Ý nghĩa / khi nào xảy ra |
|---|---|---|
| 409 | `STATE_CONFLICT` | verify-otp/cancel trên payment đã EXPIRED |
| 409 | `PAYMENT_EXPIRED` | (Biến thể tường minh) giao dịch đã bị job quét hủy do hết hạn |
| 200 | — | Các API release nội bộ trả idempotent khi job chạy lặp |

## 9. Nhánh Git & quy trình

Làm toàn bộ chức năng trên nhánh **`feature/fr08-job-quet-het-han`** — tuân thủ
[docs/fr/00-quy-trinh-git.md](00-quy-trinh-git.md): quét lại dự án + kiểm tra remote + pull main
trước khi code → giải quyết xong conflict mới push → mở PR kèm mô tả đã làm → chờ duyệt.
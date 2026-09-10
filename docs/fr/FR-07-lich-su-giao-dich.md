# FR-07 — Lịch sử giao dịch

| Mục | Nội dung |
|---|---|
| Mã chức năng | FR-07 |
| Nhánh làm việc | `feature/fr07-lich-su-giao-dich` |
| Service liên quan | payment-service + tuition-service (bổ trợ tên học kỳ) |
| Màn hình frontend | `frontend/history.html` (hoặc tab "Lịch sử" trên dashboard) |
| Tài liệu tham chiếu | BR-04, BR-15 · docs/03 mục 2.10–2.11 |

---

## 1. Chức năng là gì

Trang liệt kê **toàn bộ giao dịch của chính user** (theo uid trong JWT), hỗ trợ lọc theo trạng
thái, phân trang, và xem chi tiết từng giao dịch (bao gồm cả lý do thất bại). Dữ liệu phản ánh
trạng thái cuối cùng sau mọi tình huống: thành công, hủy, hết hạn, hụt dư… (BR-15).

## 2. Flow hoạt động

```
1. User vào trang Lịch sử → GET /payments?status=&page=1&size=20
2. payment-service đọc danh sách payment thuộc uid (từ JWT) theo bộ lọc, sắp theo created_at giảm dần
3. Frontend render bảng; bấm 1 dòng → GET /payments/{id} lấy chi tiết, hiện modal
4. Đổi trạng thái/lật trang → gọi lại với query mới
```

## 3. API cần dùng

| Method | Endpoint | Ý nghĩa trong chức năng này |
|---|---|---|
| GET | `/payments` | Danh sách giao dịch của uid + lọc + phân trang |
| GET | `/payments/{id}` | Chi tiết 1 giao dịch (kiểm tra chủ sở hữu) |

## 4. Frontend — UI cần build

1. **Bộ lọc**: các chip/tab trạng thái: Tất cả · Đang chờ · Thành công · Thất bại · Đã hủy ·
   Hết hạn (map sang các status enum) + thanh tìm kiếm không bắt buộc.
2. **Bảng lịch sử**: cột Ngày giờ tạo · Kỳ học · Số tiền · Trạng thái (badge màu) · Mã giao dịch.
   Badge màu thống nhất: PENDING xám, OTP_SENT vàng, PROCESSING xanh dương, SUCCESS xanh lá,
   FAILED đỏ, CANCELLED xám đậm, EXPIRED tím nhạt.
3. **Phân trang**: nút Trước/Sau + "Trang 1/3" (đọc `page`, `size`, `total` từ response).
4. **Modal chi tiết**: số tiền, status, `created_at`, `completed_at`, `failure_reason` (nếu có),
   tuition_id, nút đóng; dòng SUCCESS hiện thêm "Đã gửi email xác nhận".
5. Trạng thái rỗng: "Chưa có giao dịch nào" + nút quay về dashboard.

## 5. Logic backend

- Luôn lọc theo `uid` giải mã từ JWT — client **không truyền uid** (BR-04), người này không thấy
  lịch sử người khác.
- `GET /payments/{id}`: kiểm tra `payments.uid == uid` trước khi trả (403 nếu khác chủ).
- Query hỗ trợ `status` (enum payment), `page`, `size` (mặc định 20, tối đa 100) — return
  `{items, page, size, total}`.
- Trạng thái hiển thị luôn là trạng thái cuối cùng trong `payments.status` (BR-15) — đã được
  giữ nhất quán bởi FSM (BR-12) và job quét (FR-08).

## 6. Ràng buộc

| Ràng buộc | Giải thích |
|---|---|
| BR-04 | Chỉ thấy giao dịch của chính uid |
| BR-15 | Sau mọi tình huống (hủy, hết hạn, hụt dư, hủy do job) lịch sử vẫn đúng trạng thái cuối |
| Performance | Phân trang bắt buộc (`size` tối đa 100), không load cả bảng lớn |

## 7. Output mong đợi

`GET /payments?status=SUCCESS&page=1&size=20` (200):

```json
{
  "items": [
    {
      "payment_id": 42, "status": "SUCCESS", "amount": 7000000,
      "student_id": "521H0092", "tuition_id": 10,
      "created_at": "2026-08-31T10:30:00Z", "completed_at": "2026-08-31T10:32:15Z",
      "failure_reason": null
    }
  ],
  "page": 1, "size": 20, "total": 1
}
```

**Định nghĩa hoàn thành (Done):** uid3 thấy 1 giao dịch SUCCESS (khoản PAID có sẵn) và các
giao dịch khác đúng theo thực tế đã thao tác; lọc theo status đúng; gọi `/payments/{id}` của
người khác → 403; bảng không bao giờ lẫn giao dịch của uid khác.

## 8. Mã response

| HTTP | code | Ý nghĩa / khi nào xảy ra |
|---|---|---|
| 200 | — | Lấy danh sách / chi tiết thành công |
| 400 | `VALIDATION_ERROR` | `status`/`page`/`size` sai kiểu |
| 401 | `AUTH_REQUIRED` | Thiếu JWT |
| 403 | `FORBIDDEN` | Xem payment của người khác |
| 404 | `NOT_FOUND` | Không có payment với id đó |
| 500 | `INTERNAL_ERROR` | Lỗi hệ thống |
| 503 | `SERVICE_UNAVAILABLE` | PaymentDB không khả dụng |

## 9. Nhánh Git & quy trình

Làm toàn bộ chức năng trên nhánh **`feature/fr07-lich-su-giao-dich`** — tuân thủ
[docs/fr/00-quy-trinh-git.md](00-quy-trinh-git.md): quét lại dự án + kiểm tra remote + pull main
trước khi code → giải quyết xong conflict mới push → mở PR kèm mô tả đã làm → chờ duyệt.
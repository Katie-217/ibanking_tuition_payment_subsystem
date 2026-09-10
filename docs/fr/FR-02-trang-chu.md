# FR-02 — Trang chính (Dashboard: hồ sơ + số dư + học phí)

| Mục | Nội dung |
|---|---|
| Mã chức năng | FR-02 |
| Nhánh làm việc | `feature/fr02-trang-chu` |
| Service liên quan | auth-service, payer-service, tuition-service |
| Màn hình frontend | `frontend/dashboard.html` |
| Tài liệu tham chiếu | BR-04 · docs/03 mục 2.3–2.5 · docs/05 luồng "Tải màn hình thanh toán" |

---

## 1. Chức năng là gì

Màn hình chính sau đăng nhập: hiển thị **hồ sơ sinh viên** (MSSV, trường/khoa/ngành/hệ/khóa),
**số dư tài khoản** và **danh sách các khoản học phí** (học kỳ, số tiền, hạn nộp, trạng thái).
Đây là điểm xuất phát của luồng thanh toán (FR-03).

## 2. Flow hoạt động

```
1. User mở dashboard.html → kiểm tra localStorage có token không; không có → về index.html
2. Frontend gọi SONG SONG 3 API (Promise.all):
   GET /auth/me  +  GET /payers/me  +  GET /tuition/me
   (tất cả đều lấy dữ liệu của CHÍNH uid trong JWT — backend tự xác định, không nhận tham số)
3. Render 3 khối: hồ sơ sinh viên, card số dư, bảng học phí
4. Bấm [Thanh toán] tại một dòng học phí trạng thái UNPAID → chuyển modal FR-03
```

## 3. API cần dùng

| Method | Endpoint | Ý nghĩa trong chức năng này |
|---|---|---|
| GET | `/auth/me` | Tên + MSSV + role hiển thị ở header |
| GET | `/payers/me` | Số dư khả dụng hiển thị ở card số dư |
| GET | `/tuition/me` | Hồ sơ trường/khoa/ngành/hệ + danh sách học phí |

## 4. Frontend — UI cần build

Trang `dashboard.html` gồm:

1. **Header**: logo + tên sinh viên + MSSV + avatar (chữ cái đầu tên) + nút **[Đăng xuất]**.
2. **Card hồ sơ sinh viên**: MSSV to, khóa học (`enrollment_year`), 4 viên gạch thông tin
   Trường / Khoa (kèm mã khoa) / Ngành (kèm mã ngành) / Hệ đào tạo (kèm mã hệ).
3. **Card số dư**: số tiền format `Intl.NumberFormat("vi-VN")` + "₫", ví dụ **15.000.000 ₫**.
4. **Bảng học phí**, cột: Kỳ học · Số tiền · Hạn nộp · Trạng thái · Thao tác. Mỗi dòng:
   - Badge trạng thái: `UNPAID` đỏ, `PAYING` cam, `PAID` xanh lá.
   - Nút **[Thanh toán]** chỉ hiện cho dòng `UNPAID`; dòng `PAID` hiện ngày đã nộp.
   - Sắp xếp hạn nộp giảm dần (backend đã trả theo `due_date DESC`).
5. **Xử lý trạng thái tải**: skeleton loading; nếu 1 trong 3 API lỗi → thông báo tổng hợp +
   nút "Thử lại" (không render nửa chừng). 401 → tự về trang login (api-client đã xử lý).

## 5. Logic backend

- 3 endpoint đều dùng dependency `require_uid` giải mã JWT → lấy `uid`; client **không được**
  truyền uid/student_id/MSSV (chống xem dữ liệu người khác — BR-04).
- `/tuition/me`: JOIN `students → schools → faculties → majors → edu_systems` lấy đủ chuỗi
  trường/khoa/ngành/hệ, rồi đọc `tuitions WHERE student_id = ?` (theo student_id suy từ uid).
- `/payers/me`: JOIN `payers + accounts` lấy số dư; thiếu hồ sơ → 404.

## 6. Ràng buộc

| Ràng buộc | Giải thích |
|---|---|
| BR-04 | Toàn bộ dữ liệu hiển thị chỉ của `uid` trong JWT — người khác không xem lẫn nhau |
| BR-05 | Chỉ nút [Thanh toán] cho khoản `UNPAID` (không có "trả một phần") |
| UI | Số tiền luôn format đơn vị VND; không hiện số dư kiểu thô |

## 7. Output mong đợi

`GET /tuition/me` trả về (200):

```json
{
  "student": {
    "student_id": "521H0092", "full_name": "Nguyễn Văn A", "enrollment_year": "52",
    "school": {"id": "TDTU", "name": "Trường Đại học Tôn Đức Thắng"},
    "faculty": {"code": "00", "name": "Khoa Công nghệ thông tin"},
    "major": {"code": "CNTT", "name": "Công nghệ thông tin"},
    "edu_system": {"code": "1", "name": "Đại học chính quy"}
  },
  "tuitions": [
    {"tuition_id": 10, "semester": "2025-2026-HK1", "amount": 7000000,
     "status": "UNPAID", "due_date": "2025-09-30", "paid_at": null}
  ]
}
```

**Định nghĩa hoàn thành (Done):** đăng nhập uid1 thấy đúng tên A, số dư 15.000.000 và khoản
HK1 7.000.000 `UNPAID`; uid3 thấy 1 khoản `UNPAID` + 1 khoản `PAID`; không có cách nào hiển thị dữ liệu uid khác.

## 8. Mã response

| HTTP | code | Ý nghĩa / khi nào xảy ra |
|---|---|---|
| 200 | — | Lấy đủ dữ liệu 3 khối |
| 401 | `AUTH_REQUIRED` | Thiếu/ hết hạn JWT |
| 404 | `NOT_FOUND` | uid không có hồ sơ payer / sinh viên |
| 500 | `INTERNAL_ERROR` | Lỗi database |
| 503 | `SERVICE_UNAVAILABLE` | 1 trong 3 service chưa chạy/ lỗi kết nối DB |

## 9. Nhánh Git & quy trình

Làm toàn bộ chức năng trên nhánh **`feature/fr02-trang-chu`** — tuân thủ
[docs/fr/00-quy-trinh-git.md](00-quy-trinh-git.md): quét lại dự án + kiểm tra remote + pull main
trước khi code → giải quyết xong conflict mới push → mở PR kèm mô tả đã làm → chờ duyệt.
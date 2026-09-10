# FR-01 — Đăng nhập / Đăng xuất

| Mục | Nội dung |
|---|---|
| Mã chức năng | FR-01 |
| Nhánh làm việc | `feature/fr01-dang-nhap` |
| Service liên quan | auth-service (:8001) |
| Màn hình frontend | `frontend/index.html` (trang đăng nhập) |
| Tài liệu tham chiếu | BR-01, BR-02, BR-03, BR-16 · docs/03 mục 2.1–2.3 · docs/05 luồng "Đăng nhập" |

---

## 1. Chức năng là gì

Sinh viên đăng nhập bằng **username (MSSV chuẩn TDTU, ví dụ `521H0092`)** và **mật khẩu**.
Hệ thống kiểm tra thông tin trong AuthDB, cấp **JWT (HS256, 30 phút)** để gọi các API có bảo vệ.
Đăng xuất là thao tác xóa token phía client (stateless).

## 2. Flow hoạt động

```
1. User mở index.html, nhập username + password, bấm [Đăng nhập]
2. Frontend gọi POST /auth/login {username, password} qua class endpoint
3. auth-service:
   a. Kiểm tra username có khớp chuẩn MSSV TDTU không (3 số + 1 chữ + 4 số) → sai: 400
   b. JOIN users + user_credentials theo username, kiểm tra bcrypt.checkpw
   c. Sai tài khoản/mật khẩu → chung 1 thông báo 401 (không tiết lộ trường nào sai)
   d. status = LOCKED → 403
   e. OK → tạo JWT chứa {uid, username, role, exp}
4. Frontend nhận token → lưu localStorage key `ibanking_token` → chuyển sang dashboard.html
```

**Đăng xuất:** frontend gọi `POST /auth/logout` rồi xóa token khỏi localStorage và quay về index.html
(BR-16: mức môn học dùng stateless — không cần blacklist).

## 3. API cần dùng

| Method | Endpoint | Ý nghĩa trong chức năng này |
|---|---|---|
| POST | `/auth/login` | Kiểm tra đăng nhập, trả JWT (không cần auth) |
| POST | `/auth/logout` | Đồng bộ thao tác đăng xuất (Bearer JWT) |
| GET | `/auth/me` | (Tùy chọn) kiểm tra lại token/session còn hiệu lực khi mở trang |

## 4. Frontend — UI cần build

Trang `index.html`:

- Form 2 ô: **Username (MSSV)** + **Password**, nút **[Đăng nhập]** full width.
- Validate phía client: username khớp regex `^\d{3}[A-Za-z]\d{4}$`, không rỗng → hiện lỗi ngay dưới ô nhập, không gọi API.
- Trạng thái đang gửi: nút loading "Đang đăng nhập…", disable tránh double-submit.
- Xử lý lỗi từ backend (đọc envelope `{"error": {code, message}}`):
  | code | Hiển thị trên UI |
  |---|---|
  | `VALIDATION_ERROR` | "Mã số sinh viên không đúng định dạng (VD: 521H0092)" |
  | `AUTH_INVALID_CREDENTIALS` | "Sai mã số sinh viên hoặc mật khẩu" |
  | `FORBIDDEN` | "Tài khoản đã bị khóa" |
  | `SERVICE_UNAVAILABLE` | "Máy chủ đang bận, vui lòng thử lại sau" |
- Nút tải trang trước `endpoints.js` + `api-client.js`; gọi API **chỉ qua** `API_ENDPOINTS.auth.login`.

## 5. Logic backend

- Regex `^\d{3}[A-Za-z]\d{4}$` chặn ngay format sai (BR-01) — không chạm DB.
- Mật khẩu so bằng `bcrypt.checkpw` với hash trong bảng `user_credentials` (BR-02 — bảng tách riêng profile/password).
- Không trả thông tin nào phân biệt "sai user" / "sai mật khẩu" (chống dò tài khoản).
- JWT sinh bằng `create_access_token()` trong `services/shared/security.py`, HS256, exp = `JWT_EXPIRES_MINUTES` phút.

## 6. Ràng buộc

| Ràng buộc | Giải thích |
|---|---|
| BR-01 | username phải chuẩn MSSV TDTU; vi phạm → 400 |
| BR-02 | mật khẩu chỉ lưu hash bcrypt trong bảng `user_credentials` riêng |
| BR-03 | các API còn lại chỉ chạy khi JWT hợp lệ (dependency `require_uid`) |
| BR-16 | logout = xóa token client (stateless, không session server) |
| Bảo mật | thông báo lỗi đăng nhập chung chung; không log mật khẩu thô |

## 7. Output mong đợi

Thành công (200):

```json
{
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "expires_in": 1800,
  "user": {"uid": 1, "username": "521H0092", "full_name": "Nguyễn Văn A", "role": "student"}
}
```

**Định nghĩa hoàn thành (Done):** đăng nhập đúng MSSV/mật khẩu demo vào được dashboard;
sai mật khẩu / sai format / tài khoản khóa hoặc thiếu hash bcrypt đều báo đúng mã lỗi ở bảng dưới.

## 8. Mã response

| HTTP | code | Ý nghĩa / khi nào xảy ra |
|---|---|---|
| 200 | — | Đăng nhập thành công (hoặc logout OK) |
| 400 | `VALIDATION_ERROR` | Username không khớp chuẩn MSSV TDTU |
| 401 | `AUTH_INVALID_CREDENTIALS` | Sai username hoặc mật khẩu (thông báo chung) |
| 401 | `AUTH_REQUIRED` | Gọi API bảo vệ thiếu/ sai JWT |
| 403 | `FORBIDDEN` | Tài khoản `LOCKED` |
| 500 | `INTERNAL_ERROR` | Lỗi truy cập database |
| 503 | `SERVICE_UNAVAILABLE` | Không kết nối được AuthDB |

## 9. Nhánh Git & quy trình

Làm toàn bộ chức năng trên nhánh **`feature/fr01-dang-nhap`**, tuân thủ quy trình ở
[docs/fr/00-quy-trinh-git.md](00-quy-trinh-git.md): quét lại dự án + kiểm tra remote + pull main
trước khi code → giải quyết xong conflict mới push → mở PR kèm mô tả đã làm → chờ duyệt.
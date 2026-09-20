# Phân Công Công Việc — Sprint 2: 20/09/2026 → 27/09/2026 (Tuần 1 / 3)

> **Bảng phân việc chính thức của nhóm cho Sprint 2 (Frontend UI & API Integration Song Song).**
> Mỗi người làm đúng phân hệ được giao, làm việc song song không nghẽn nhau, làm xong tick vào ô output và ghi nhật ký.

---

## 0. Quy Trình Bắt Buộc Khi Ngồi Vào Làm (4 Bước)

| Bước | Việc | File |
|---|---|---|
| 1 | **Quét nhật ký** để biết tiến độ dự án & cấu hình MongoDB | [docs/NHAT-KY-CONG-VIEC.md](NHAT-KY-CONG-VIEC.md) |
| 2 | **Quét file phân công này** → Tìm task của mình, đọc mô tả + output + ranh giới file | file này |
| 3 | **Khởi chạy hệ thống Backend**: Gõ `docker compose up -d` hoặc `python scripts/init_mongodb.py` | `docker-compose.yml` |
| 4 | Làm xong: **Tick ✅ output** trong file này + **Ghi entry nhật ký** + Mở PR | 2 file trên |

Quy trình git (tạo nhánh, pull main, giải conflict, mở PR duyệt): [docs/fr/00-quy-trinh-git.md](fr/00-quy-trinh-git.md).

---

## 1. Tổng Quan Phân Công Tuần Này (Sprint 2: 20/09 → 27/09)

| Task | Người Làm | Nội Dung Chi Tiết | Bắt Đầu | Deadline | Nhánh | Trạng Thái |
|---|---|---|---|---|---|---|
| **TASK-FRONTEND-1** | **Bạn (Dev 1 / Katie)** | Login UI + Dashboard Profile & Nợ Học Phí + Popup Môn Học (`login.html`, `dashboard.html`, `auth.js`, `tuition.js`) | 20/09 | 27/09 | `feat/frontend-auth-tuition` | 🔄 Đang làm |
| **TASK-FRONTEND-2** | **Bạn của Bạn (Dev 2)** | Thanh Toán Học Phí, OTP Modal, Hủy/Gửi lại OTP, Lịch Sử Giao Dịch & Biên Lai (`history.html`, `payment.js`, `otp.js`, `history.js`) | 20/09 | 27/09 | `feat/frontend-payment-otp-history` | 🔄 Đang làm |

---

## 2. TASK-FRONTEND-1 — Auth, User Profile & Tuition Dashboard UI

| Mục | Nội dung |
|---|---|
| Người làm | **Bạn (Dev 1 / Katie)** |
| Thời gian | **20/09/2026 → 27/09/2026 (23:59)** |
| Nhánh Git | `feat/frontend-auth-tuition` |
| Trạng thái | 🔄 Đang làm |

### 2.1 Phạm vi & Vùng file được tạo/sửa:
- `frontend/login.html` & `frontend/dashboard.html`
- `frontend/js/auth.js` & `frontend/js/tuition.js`
- `frontend/css/style.css` (Style UI chung)

### 2.2 Output cần đạt — Làm xong tick vào ô:
- [ ] **Màn hình Đăng nhập (`login.html`)**:
  - Giao diện đăng nhập hiện đại với MSSV (như `521H0092` hoặc `523H0058`) & mật khẩu (`Password123@`).
  - Tích hợp API `POST /auth/login` qua API Gateway (`:8000`).
  - Lưu JWT Token vào `localStorage` và chuyển hướng sang Dashboard khi login đúng.
  - Hiển thị thông báo lỗi mượt mà khi sai MSSV hoặc sai mật khẩu.
- [ ] **Màn hình Trang chủ Dashboard (`dashboard.html`)**:
  - Tích hợp API `GET /auth/me` & `GET /payers/me`: Hiển thị Họ tên sinh viên, MSSV, Email, SĐT và **Số dư tài khoản (VND)**.
  - Tích hợp API `GET /tuition/me`: Hiển thị phiếu học phí chưa thanh toán (Tổng nợ học phí, Học kỳ, Tên trường).
- [ ] **Modal Popup Chi Tiết Môn Học**:
  - Tích hợp API `GET /tuitions/{id}/enrollments`: Hiển thị danh sách các môn học đăng ký (Mã môn, Tên môn, Tín chỉ, Số tiền) + Thông tin tài khoản thụ hưởng nhà trường.

---

## 3. TASK-FRONTEND-2 — Payment Execution, OTP Modal & History UI

| Mục | Nội dung |
|---|---|
| Người làm | **Bạn của bạn (Dev 2)** |
| Thời gian | **20/09/2026 → 27/09/2026 (23:59)** |
| Nhánh Git | `feat/frontend-payment-otp-history` |
| Trạng thái | 🔄 Đang làm |

### 3.1 Phạm vi & Vùng file được tạo/sửa:
- `frontend/payment.html` (hoặc Modal Popup Thanh toán OTP)
- `frontend/history.html`
- `frontend/js/payment.js`, `frontend/js/otp.js`, `frontend/js/history.js`

### 3.2 Output cần đạt — Làm xong tick vào ô:
- [ ] **Luồng Khởi Tạo Thanh Toán & OTP Modal**:
  - Nút "Thanh toán học phí": Gọi API `POST /payments` với `tuition_id`.
  - Hiển thị **Modal Popup OTP 6 số**: Đồng hồ đếm ngược 5 phút (300s).
  - Nút "Xác thực OTP": Gọi API `POST /payments/{id}/verify-otp`.
- [ ] **Luồng Gửi Lại OTP & Hủy Giao Dịch**:
  - Nút "Gửi lại OTP": Gọi API `POST /payments/{id}/resend-otp` (Throttle 30s).
  - Nút "Hủy giao dịch": Gọi API `POST /payments/{id}/cancel`.
- [ ] **Màn Hình Lịch Sử & Biên Lai Giao Dịch (`history.html`)**:
  - Hiển thị màn hình kết quả biên lai khi thanh toán thành công.
  - Gọi API `GET /payments` hiển thị danh sách lịch sử giao dịch (Trạng thái `SUCCESS`, `FAILED`, `CANCELLED`, `EXPIRED`).

---

## 4. Bảng Ranh Giới File Toàn Nhóm (Tránh Conflict Git)

| File / Thư mục | Dev 1 (Bạn) | Dev 2 (Bạn của bạn) |
|---|---|---|
| `frontend/login.html`, `frontend/dashboard.html` | ✅ Được sửa | ⛔ Không sửa |
| `frontend/js/auth.js`, `frontend/js/tuition.js` | ✅ Được sửa | ⛔ Không sửa |
| `frontend/history.html` | ⛔ Không sửa | ✅ Được sửa |
| `frontend/js/payment.js`, `frontend/js/otp.js`, `frontend/js/history.js` | ⛔ Không sửa | ✅ Được sửa |
| `frontend/js/endpoints.js`, `frontend/js/api-client.js` | 👀 Chỉ đọc | 👀 Chỉ đọc |
| `services/**` (Backend Microservices) | 👀 Chỉ đọc | 👀 Chỉ đọc |
| `docker-compose.yml`, `scripts/**` | 👀 Chỉ đọc | 👀 Chỉ đọc |
| `docs/NHAT-KY-CONG-VIEC.md` | ✅ Thêm entry | ✅ Thêm entry |
| `docs/PHAN-CONG-CONG-VIEC.md` | ✅ Tick TASK 1 | ✅ Tick TASK 2 |

---

## 5. Hợp Đồng Chung — Không Ai Được Tự Đổi

| Hạng mục | Quy định |
|---|---|
| Tên & Đường dẫn Endpoint | Gọi API qua API Gateway `:8000` sử dụng các định nghĩa có sẵn trong `frontend/js/endpoints.js`. |
| Cấu trúc lỗi | Luôn đọc `error.code` và `error.message` từ response. |
| Tài khoản test mẫu | Sử dụng `521H0092` hoặc `523H0058` với mật khẩu `Password123@`. |

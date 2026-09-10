# 11 — Tài liệu Endpoint & Resource: khái niệm + Danh mục toàn bộ API

> File này gồm 2 phần:
> **Phần A** — giải thích khái niệm *API, endpoint, resource* và ý nghĩa của chúng.
> **Phần B** — **DANH MỤC DUY NHẤT toàn bộ API** của hệ thống (1 file): mỗi dòng = 1 API,
> 3 cột Method · Endpoint · Ý nghĩa. (Spec chi tiết request/response xem
> [docs/03-thiet-ke-rest-api.md](03-thiet-ke-rest-api.md); cách gọi từ frontend xem
> [docs/09](09-readme-bieu-dien-api-endpoint-lop.md).)

---

# Phần A — Khái niệm: endpoint & resource là gì

## 1. API

**API (Application Programming Interface)** = "cửa" để 2 phần mềm nói chuyện với nhau qua quy
ước đã thỏa thuận. Trong dự án: frontend muốn biết số dư → gọi API; service này muốn trừ tiền
của service kia → cũng gọi API. API không phải là database — client không bao giờ chạm trực
tiếp SQL Server, chỉ chạm API.

## 2. Endpoint

**Endpoint** = **một địa chỉ cụ thể** (URL) + **một phương thức HTTP** mà client gọi vào để thực
hiện 1 thao tác. Ví dụ:

```
POST  http://localhost:8000/payments/42/verify-otp
└┬─┘  └────────┬────────────────┬─────┬─┬┴──────────┘
method        host (gateway)         path với
                                      path parameter
```

- **Method** (GET/POST/…) — *hành động cần làm*.
- **Path** — *đối tượng chịu tác động* (resource) và/hoặc hành động phụ.

Endpoint là thứ duy nhất frontend được phép gọi — và phải gọi qua lớp tập trung
`frontend/js/endpoints.js` (xem [docs/09](09-readme-bieu-dien-api-endpoint-lop.md)).

## 3. Resource

**Resource** = *đối tượng nghiệp vụ* mà API thao tác, luôn đặt tên bằng **danh từ số nhiều**:
`users`, `payers`, `tuitions`, `payments`, `otps`, `email_outbox`.

Ví dụ phân tích endpoint `GET /payments/42`:

| Thành phần | Giá trị | Ý nghĩa |
|---|---|---|
| Resource | `payments` | "bảng" các giao dịch thanh toán |
| Path parameter | `42` | định danh 1 giao dịch cụ thể (payment_id) |
| Method | GET | chỉ đọc, không làm thay đổi gì |

## 4. Các thành phần khác trong 1 đường dẫn

| Thành phần | Ví dụ | Ý nghĩa |
|---|---|---|
| **Path parameter** | `/payments/{payment_id}/verify-otp` | Giá trị **bắt buộc** nằm trong đường dẫn — xác định một đối tượng cụ thể |
| **Query parameter** | `/payments?status=SUCCESS&page=1` | Tham số **tùy chọn** sau dấu `?` — lọc/sắp xếp/phân trang, không xác định đối tượng đơn lẻ |
| **Header** | `Authorization: Bearer <JWT>` | Thông tin đi kèm request: xác thực, `Idempotency-Key`, `X-Internal-Token` |
| **Body** | `{"tuition_id": 10}` | Dữ liệu gửi kèm (chỉ với POST/PUT/PATCH) |
| **Sub-resource** | `/payments/{id}/verify-otp` | Hành động phụ gắn với resource (xác thực OTP *của* giao dịch này) |

## 5. Các Method và ý nghĩa

| Method | Ý nghĩa | An toàn? | Idempotent? |
|---|---|---|---|
| **GET** | Đọc dữ liệu, không thay đổi gì trên server | ✅ an toàn | ✅ gọi 100 lần ra cùng kết quả |
| **POST** | Tạo mới / thực hiện 1 hành động có hệ quả (trừ tiền, verify OTP) | ❌ thay đổi trạng thái | ❌ thường KHÔNG — phải tự chống bằng Idempotency-Key / payment_id |
| **PUT/PATCH** | (Dự phòng) cập nhật toàn bộ/một phần | ❌ | ✅ nên có |
| **DELETE** | (Dự phòng) xóa | ❌ | ✅ nên có |

> Lưu ý thực tế trong dự án: các hành động nghiệp vụ (lock/paid/release/cancel/resend/verify)
> KHÔNG dùng DELETE trực tiếp lên resource vì cần ghi lịch sử — dùng **POST tới sub-resource**
> để tường minh, vẫn tuân chuẩn REST.

## 6. Quy ước thiết kế đường dẫn của dự án

1. Resource là **danh từ số nhiều** (`/payments`, `/tuitions`, `/payers`), không đặt động từ vào
   path tài nguyên (`/getPayments` ❌).
2. Thao tác riêng của resource → **sub-resource**: `/payments/{id}/verify-otp`.
3. Đường dẫn **nội bộ** giữa các service luôn có tiền tố `/internal/` và không đi qua gateway.
4. Dữ liệu nhạy cảm về danh tính (`uid`, `student_id`, `payer_uid`) **không nằm trong path/query
   của API người dùng** — luôn suy từ JWT (BR-04), tránh lộ và tránh gọi hộ người khác.
5. Auth: API người dùng dùng `Authorization: Bearer <JWT>`; API `/internal/*` dùng header
   `X-Internal-Token` + `X-Correlation-Id`.
6. Query chỉ dùng cho **lọc/phân trang**, không dùng cho hành động thay trạng thái.

---

# Phần B — Danh mục toàn bộ API (dùng chung 1 file)

> ✅ = đã code xong và test được · 🚧 = đã thiết kế, đang phát triển

## B.0 API Gateway (:8000)

| Method | Endpoint | Ý nghĩa |
|---|---|---|
| 🚧 GET | `/health` | Tổng hợp trạng thái sống/chết của 7 service |

## B.1 auth-service (:8001)

| Method | Endpoint | Ý nghĩa |
|---|---|---|
| ✅ POST | `/auth/login` | Đăng nhập (username=MSSV + password) → cấp JWT |
| ✅ POST | `/auth/logout` | Đăng xuất — frontend xóa token (stateless) |
| ✅ GET | `/auth/me` | Đọc thông tin user đang đăng nhập (từ JWT) |
| ✅ GET | `/health` | Kiểm tra service sống + kết nối AuthDB |
| 🚧 POST | `/internal/verify-jwt` | (Gateway dùng) kiểm tra JWT hợp lệ trả claims |

## B.2 payer-service (:8002)

| Method | Endpoint | Ý nghĩa |
|---|---|---|
| ✅ GET | `/payers/me` | Hồ sơ người nộp + số dư của CHÍNH user (uid từ JWT) |
| ✅ GET | `/health` | Kiểm tra service sống + kết nối PayerDB |
| 🚧 GET | `/internal/payers/{uid}` | (Nội bộ) đọc profile payer + số dư theo uid |
| 🚧 POST | `/internal/balance/reserve` | (Tùy chọn, mô hình 2 pha) đánh dấu giữ chỗ số tiền |
| ✅ POST | `/internal/balance/capture` | (Nội bộ) TRỪ tiền nguyên tử — idempotent theo payment_id, 422 nếu thiếu dư |
| ✅ POST | `/internal/balance/release` | (Nội bộ) HOÀN tiền bù trừ — idempotent theo payment_id |

> ✅ = đã chạy và được `scripts/test_api.py` kiểm tra (T07, T09–T14).

## B.3 tuition-service (:8003)

| Method | Endpoint | Ý nghĩa |
|---|---|---|
| ✅ GET | `/tuition/me` | Hồ sơ sinh viên (trường/khoa/ngành/hệ/mã hệ) + danh sách học phí của CHÍNH user |
| ✅ GET | `/health` | Kiểm tra service sống + kết nối TuitionDB |
| ✅ GET | `/internal/tuitions/{tuition_id}?uid=` | (Nội bộ) đọc 1 khoản học phí + kiểm tra chủ sở hữu (403 nếu khác uid) |
| ✅ POST | `/internal/tuitions/{tuition_id}/lock` | (Nội bộ) khóa khoản học phí UNPAID→PAYING (chống thanh toán 2 lần song song) |
| ✅ POST | `/internal/tuitions/{tuition_id}/paid` | (Nội bộ) đánh dấu đã nộp PAYING→PAID + lưu paid_by_payment_id |
| ✅ POST | `/internal/tuitions/{tuition_id}/release` | (Nội bộ) bù trừ mở khóa PAYING→UNPAID khi giao dịch fail/cancel/hết hạn |

## B.4 payment-service (:8004) — orchestrator

| Method | Endpoint | Ý nghĩa |
|---|---|---|
| 🚧 POST | `/payments` | Tạo giao dịch thanh toán (khóa tuition + trừ tiền + gửi OTP) — kèm `Idempotency-Key` |
| 🚧 POST | `/payments/{payment_id}/verify-otp` | Xác thực OTP → chốt thanh toán (tuition PAID, payment SUCCESS, gửi mail) |
| 🚧 POST | `/payments/{payment_id}/resend-otp` | Đánh dấu OTP cũ `REPLACED` + sinh OTP mới + gửi lại email (tối đa 1 lần/30s) |
| 🚧 POST | `/payments/{payment_id}/cancel` | Hủy giao dịch đang chờ — mở khóa tuition, đánh dấu OTP `CANCELLED`; chỉ hoàn tiền nếu payment đã có CAPTURE |
| 🚧 GET | `/payments/{payment_id}` | Chi tiết 1 giao dịch (chỉ chủ sở hữu) |
| 🚧 GET | `/payments` | Lịch sử giao dịch của user — lọc `?status=&page=&size=` |
| 🚧 GET | `/health` | Kiểm tra service sống + kết nối PaymentDB |
| 🚧 *task nền* | — *(sweep job 5–10s, không phải endpoint)* | Quét giao dịch PENDING/OTP_SENT quá hạn → EXPIRED + bù trừ (FR-08) |

## B.5 otp-service (:8005)

| Method | Endpoint | Ý nghĩa |
|---|---|---|
| 🚧 POST | `/internal/otp/generate` | Nhận `uid` + payment, đánh dấu OTP cũ `REPLACED` rồi sinh OTP 6 số (hạn 5 phút, không trùng mã ACTIVE) |
| 🚧 POST | `/internal/otp/verify` | Kiểm tra mã: sai đếm lần (≥5 → `LOCKED`); đúng → `USED`; hết hạn → `EXPIRED` |
| 🚧 POST | `/internal/otp/invalidate` | Đánh dấu OTP `CANCELLED` khi hủy giao dịch/hết hạn |
| 🚧 GET | `/health` | Kiểm tra service sống + kết nối OTPDB |

## B.6 notification-service (:8006)

| Method | Endpoint | Ý nghĩa |
|---|---|---|
| 🚧 POST | `/internal/notifications/otp-email` | Gửi email chứa mã OTP (Gmail SMTP, template riêng) |
| 🚧 POST | `/internal/notifications/confirm-email` | Gửi email xác nhận thanh toán cho sinh viên + CC nhà trường |
| 🚧 GET | `/health` | Kiểm tra service sống + kết nối NotificationDB |

---

## Ghi chú đồng bộ

- Mọi thay đổi đường dẫn/API mới → cập nhật **cùng lúc 3 nơi**: file này (bảng trên) +
  [docs/03](03-thiet-ke-rest-api.md) (spec chi tiết) + `frontend/js/endpoints.js` (lớp endpoint).
- Mã lỗi trả về của từng endpoint: xem [docs/10-quy-dinh-ma-phan-hoi.md](10-quy-dinh-ma-phan-hoi.md).
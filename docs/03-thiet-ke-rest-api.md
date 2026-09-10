# Tài liệu 03 — Thiết kế REST API

> Đáp ứng yêu cầu đề bài mục 3: URI, HTTP Method, Input/Request, Output/Response, HTTP Status Code cho từng API, kèm validation, business rule, error response.

## 1. Quy ước chung

### 1.1 Chuẩn lỗi (error envelope)

```json
{
  "error": {
    "code": "INSUFFICIENT_BALANCE",
    "message": "Số dư khả dụng không đủ để thanh toán",
    "detail": "required=7000000, available=1200000"
  }
}
```

### 1.2 Bảng mã lỗi nghiệp vụ

| HTTP | code (body) | Ý nghĩa |
|---|---|---|
| 400 | `VALIDATION_ERROR` | Sai format đầu vào (username, amount…) |
| 400 | `OTP_INVALID` | OTP sai/mã không tồn tại |
| 400 | `OTP_EXPIRED` | OTP hết hạn |
| 400 | `OTP_USED` | OTP đã dùng |
| 400 | `OTP_LOCKED` | Nhập sai quá số lần cho phép |
| 401 | `AUTH_REQUIRED` | Thiếu/ sai JWT |
| 401 | `AUTH_INVALID_CREDENTIALS` | Sai username hoặc password |
| 403 | `FORBIDDEN` | Không có quyền với tài nguyên |
| 404 | `NOT_FOUND` | Không tìm thấy đối tượng |
| 409 | `TUITION_ALREADY_PAID` | Học phí đã thanh toán |
| 409 | `PAYMENT_ALREADY_ACTIVE` | Đã có giao dịch đang chờ cho khoản học phí này |
| 409 | `PAYMENT_CONFLICT_CONCURRENT` | Khoản học phí vừa được thanh toán bởi giao dịch khác |
| 409 | `STATE_CONFLICT` | Giao dịch không ở trạng thái cho phép thao tác (sai FSM) |
| 422 | `INSUFFICIENT_BALANCE` | Số dư khả dụng không đủ để thanh toán (detail: `required=..., available=...`) |
| 422 | `BUSINESS_RULE_VIOLATION` | Vi phạm rule nghiệp vụ khác |
| 429 | `RATE_LIMITED` | Quá số lần gọi cho phép |
| 500 | `INTERNAL_ERROR` | Lỗi hệ thống |
| 503 | `SERVICE_UNAVAILABLE` | Service nội bộ không khả dụng |

### 1.3 Quy ước chung khác

- **Auth cho endpoint công khai:** header `Authorization: Bearer <JWT>` (JWT cấp bởi `POST /auth/login`, exp 30 phút).
- **Auth cho endpoint nội bộ:** header `X-Internal-Token` (secret chia sẻ qua env) + `X-Correlation-Id: <payment_id>`.
- Nội dung trả về luôn JSON (trừ khi có ghi chú).
- Các API gọi qua **API Gateway :8000**; đường nội bộ gọi trực tiếp port service (không qua gateway).

## 2. API lớp người dùng (qua Gateway)

### 2.1 `POST /auth/login`
| Mục | Nội dung |
|---|---|
| Service | auth-service |
| Auth | Không yêu cầu |
| Request | `{"username": "521H0092", "password": "********"}` |
| Validation | username khớp regex MSSV TDTU `^\d{3}[A-Za-z]\d{4}$`; password không rỗng |
| Business rule | BR-01, BR-02; bcrypt so khớp; sai thông tin → generic message (không tiết lộ trường nào sai) |
| Response 200 | `{"token": "<jwt>", "expires_in": 1800, "user": {"uid": 1, "username": "521H0092", "full_name": "Nguyễn Văn A", "role": "student"}}` |
| Errors | 400 `VALIDATION_ERROR`; 401 `AUTH_INVALID_CREDENTIALS`; 500/503 |

### 2.2 `POST /auth/logout`
| Mục | Nội dung |
|---|---|
| Service | auth-service |
| Auth | Bearer JWT |
| Request | (không body) |
| Response 200 | `{"message": "Đã đăng xuất"}` |
| Ghi chú | Frontend xóa token khỏi storage; tùy chọn nâng cấp: blacklist jti trong Redis/bảng |

### 2.3 `GET /auth/me`
| Mục | Nội dung |
|---|---|
| Service | auth-service |
| Auth | Bearer JWT |
| Response 200 | `{"uid": 1, "username": "521H0092", "full_name": "...", "phone": "...", "email": "...", "role": "student"}` |
| Errors | 401 `AUTH_REQUIRED` |

### 2.4 `GET /payers/me`
| Mục | Nội dung |
|---|---|
| Service | payer-service |
| Auth | Bearer JWT (uid trích từ JWT — **client không truyền uid**) |
| Response 200 | `{"payer_uid": 1, "full_name": "Nguyễn Văn A", "phone": "0901...", "email": "521H0092@student.tdtu.edu.vn", "available_balance": 15000000}` |
| Business rule | BR-04; thông tin lấy duy nhất từ uid trong JWT |
| Errors | 401; 404 `NOT_FOUND` (uid không có hồ sơ payer) |

### 2.5 `GET /tuition/me`
| Mục | Nội dung |
|---|---|
| Service | tuition-service |
| Auth | Bearer JWT (uid từ JWT) |
| Response 200 | `{"student": {"student_id": "521H0092", "full_name": "Nguyễn Văn A", "enrollment_year": "52", "school": {"id": "TDTU", "name": "Trường Đại học Tôn Đức Thắng"}, "faculty": {"code": "00", "name": "Khoa Công nghệ thông tin"}, "major": {"code": "CNTT", "name": "Công nghệ thông tin"}, "edu_system": {"code": "1", "name": "Đại học chính quy"}}, "tuitions": [{"tuition_id": 10, "semester": "2025-2026-HK1", "amount": 7000000, "status": "UNPAID", "due_date": "2025-09-30", "paid_at": null}]}` |
| Business rule | Chỉ trả tuition của chính uid (BR-04); UI dùng tuitions `UNPAID` làm "số tiền cần thanh toán" |
| Errors | 401; 404 nếu uid không map student |

### 2.6 `POST /payments` — tạo giao dịch (kèm gửi OTP)
| Mục | Nội dung |
|---|---|
| Service | payment-service (orchestrator) |
| Auth | Bearer JWT |
| Request | `{"tuition_id": 10}` hoặc `{}` (server tự chọn khoản UNPAID đầu tiên của uid; **không nhận** payer_uid/student_id/MSSV) |
| Header tùy chọn | `Idempotency-Key: <uuid>` — retry trả về payment đã tạo thay vì tạo mới |
| Pre-conditions | (a) tuition tồn tại & `UNPAID` & thuộc uid; (b) user không có payment active nào khác; (c) user không có OTP ACTIVE nào khác. Số dư hiện tại chỉ dùng để hiển thị, không phải cam kết đủ tiền vì có thể thay đổi trước khi xác thực OTP |
| Luồng | Gọi payer (đọc số dư tham khảo) → tuition (đọc tuition) → tạo payment `PENDING` → lock tuition (`UNPAID→PAYING`) → sinh OTP qua otp-service → gửi email OTP qua notification-service → payment `OTP_SENT` → trả payment_id. **Chưa capture/trừ tiền ở bước này.** |
| Response 201 | `{"payment_id": 42, "status": "OTP_SENT", "amount": 7000000, "student_id": "521H0092", "tuition_id": 10, "otp_expires_in_seconds": 300, "created_at": "..."}` |
| Errors | 404 `NOT_FOUND`; 409 `TUITION_ALREADY_PAID`, `PAYMENT_ALREADY_ACTIVE`; 503 nếu notification thất bại → invalidate OTP, release tuition, payment `FAILED` |

### 2.7 `POST /payments/{id}/verify-otp`
| Mục | Nội dung |
|---|---|
| Service | payment-service |
| Auth | Bearer JWT (kiểm tra payment thuộc uid) |
| Request | `{"otp": "482913"}` |
| Pre-conditions | payment đang `OTP_SENT`; OTP hợp lệ & còn hạn (BR-08) |
| Luồng | verify OTP (otp-service) → đánh dấu USED → payment `PROCESSING` → capture balance (payer) → tuition `PAID` → payment `SUCCESS` → lưu history → gửi email xác nhận cho **sinh viên + nhà trường** (async, lỗi email không làm payment fail) → trả receipt |
| Response 200 | `{"payment_id": 42, "status": "SUCCESS", "amount": 7000000, "student": {"student_id": "521H0092", "full_name": "..."}, "tuition_id": 10, "balance_after": 8000000, "completed_at": "..."}` |
| Errors | 403 (không phải chủ); 400 `OTP_INVALID/OTP_EXPIRED/OTP_USED/OTP_LOCKED`; 409 `STATE_CONFLICT`, `PAYMENT_CONFLICT_CONCURRENT`; 422 `INSUFFICIENT_BALANCE` (dư không đủ tại thời điểm capture → payment `FAILED`, release tuition, không release balance vì chưa capture) |

### 2.8 `POST /payments/{id}/resend-otp`
| Mục | Nội dung |
|---|---|
| Service | payment-service |
| Auth | Bearer JWT |
| Pre-condition | payment `OTP_SENT`; tần suất tối đa 1 lần/30s mỗi payment |
| Luồng | Khi payment còn `OTP_SENT`, kể cả OTP cũ đã `EXPIRED`: chuyển OTP cũ sang trạng thái terminal (`REPLACED`/`EXPIRED`) → sinh OTP mới cho **cùng payment_id** → gửi lại email. Không tạo payment mới và không capture tiền |
| Response 200 | `{"payment_id": 42, "otp_expires_in_seconds": 300}` |
| Errors | 409 `STATE_CONFLICT`; 429 `RATE_LIMITED` |

### 2.9 `POST /payments/{id}/cancel`
| Mục | Nội dung |
|---|---|
| Service | payment-service |
| Auth | Bearer JWT |
| Pre-condition | payment `PENDING`/`OTP_SENT` |
| Luồng | invalidate OTP (nếu có) → release tuition (`PAYING→UNPAID`) → payment `CANCELLED` |
| Response 200 | `{"payment_id": 42, "status": "CANCELLED"}` |
| Errors | 403; 409 `STATE_CONFLICT` |

### 2.10 `GET /payments/{id}`
| Mục | Nội dung |
|---|---|
| Service | payment-service |
| Auth | Bearer JWT, chỉ chủ payment (uid khớp) |
| Response 200 | `{"payment_id": 42, "status": "SUCCESS", "amount": 7000000, "student_id": "...", "tuition_id": 10, "created_at": "...", "completed_at": "...", "failure_reason": null}` |
| Errors | 403; 404 |

### 2.11 `GET /payments` — lịch sử giao dịch của user
| Mục | Nội dung |
|---|---|
| Service | payment-service |
| Auth | Bearer JWT |
| Query | `?status=SUCCESS&page=1&size=20` (lọc theo uid trong JWT) |
| Response 200 | `{"items": [ {payment...} ], "page": 1, "size": 20, "total": 3}` |
| Errors | 401 |

### 2.12 `GET /health`
| Mục | Nội dung |
|---|---|
| Service | gateway (tổng hợp trạng thái 7 service) |
| Response 200 | `{"status": "ok", "services": {"auth": "up", "payer": "up", ...}}` |

## 3. API nội bộ (service-to-service, không qua Gateway)

> Mọi call đều có header: `X-Internal-Token: <secret>`, `X-Correlation-Id: <payment_id>`.

### 3.1 payer-service
| Method | Endpoint | Input | Output | Ghi chú |
|---|---|---|---|---|
| GET | `/internal/payers/{uid}` | uid | Payer profile + balance | Payment service đọc thông tin payer/email |
| POST | `/internal/balance/reserve` | `{payment_id, uid, amount}` | `{reserved: true}` | Đánh dấu giữ chỗ (tùy chọn, nếu dùng mô hình 2 pha) |
| POST | `/internal/balance/capture` | `{payment_id, uid, amount}` | `{captured: true, balance_after}` | **Trừ tiền nguyên tử**; idempotent theo payment_id; 422 nếu không đủ dư |
| POST | `/internal/balance/release` | `{payment_id, uid, amount}` | `{released: true}` | Bù trừ; idempotent; không trả lại nếu payment chưa capture |

### 3.2 tuition-service
| Method | Endpoint | Input | Output | Ghi chú |
|---|---|---|---|---|
| POST | `/internal/tuitions/{tuition_id}/lock` | `{uid, payment_id}` | `{tuition_id, status: "PAYING"}` | `UNPAID→PAYING` (conditional update); 403 nếu tuition không thuộc uid; 409 nếu đã PAYING/PAID |
| POST | `/internal/tuitions/{tuition_id}/paid` | `{uid, payment_id}` | `{tuition_id, status: "PAID"}` | `PAYING→PAID` + lưu `paid_by_payment_id`; idempotent theo payment_id |
| POST | `/internal/tuitions/{tuition_id}/release` | `{uid, payment_id}` | `{tuition_id, status: "UNPAID"}` | `PAYING→UNPAID` khi payment fail/cancel/hết hạn; idempotent |
| GET | `/internal/tuitions/{tuition_id}?uid=` | – | Tuition detail | Kiểm tra chủ sở hữu ngay khi đọc; 403 nếu khác uid (BR-04) |

### 3.3 otp-service
| Method | Endpoint | Input | Output | Ghi chú |
|---|---|---|---|---|
| POST | `/internal/otp/generate` | `{uid, payment_id, email, purpose: "TUITION_PAYMENT"}` | `{otp_id, code, expires_at}` | Chuyển OTP `ACTIVE` cũ sang `REPLACED` rồi sinh mới; unique `uid`/`payment_id`/`code` chỉ áp dụng khi `ACTIVE` |
| POST | `/internal/otp/verify` | `{payment_id, code}` | `{verified: true}` | Sai ≥ 5 lần → status `LOCKED`; xác thực thành công → status `USED`; hết hạn → status `EXPIRED` + trả `OTP_EXPIRED` |
| POST | `/internal/otp/invalidate` | `{payment_id}` | `{updated: true, status: "CANCELLED"}` | Cập nhật OTP `ACTIVE` thành `CANCELLED` khi hủy giao dịch |

### 3.4 notification-service
| Method | Endpoint | Input | Output | Ghi chú |
|---|---|---|---|---|
| POST | `/internal/notifications/otp-email` | `{payment_id, to_email, to_name, otp_code, expires_in}` | `{sent: true, message_id}` | Template email OTP |
| POST | `/internal/notifications/confirm-email` | `{payment_id, to_email, to_name, cc_school_email, amount, student_id, tuition_id, completed_at}` | `{sent: true}` | Gửi cho SV + nhà trường; ghi outbox; retry nếu Gmail lỗi tạm thời |

### 3.5 auth-service (nội bộ cho gateway)
| Method | Endpoint | Input | Output |
|---|---|---|---|
| POST | `/internal/verify-jwt` | `{token}` | `{"valid": true, "claims": {"uid": 1, "username": "...", "exp": ...}}` |

## 4. Kỹ thuật REST áp dụng (checklist khi code)

1. **Tài nguyên danh từ, số nhiều** — `/payers`, `/tuitions`, `/payments`; hành động dạng sub-resource (`/payments/{id}/verify-otp`).
2. **Method đúng ngữ nghĩa** — POST tạo, GET đọc, không dùng GET để thay đổi trạng thái.
3. **Status code chuẩn** — 201 khi tạo, 200/204 khi xử lý xong, 409 cho conflict nghiệp vụ, 422 cho vi phạm rule.
4. **HATEOAS tối thiểu** — response chính kèm `links` (self, verify-otp) khi có thể (không bắt buộc ở đồ án).
5. **Idempotency** cho POST tạo payment và cho mọi call nội bộ (key = `payment_id`).
6. **Stateless** — không session, mọi định danh từ JWT; không nhận id nhạy cảm từ client.
7. **Validation tập trung** — dùng Pydantic schema từng service, trả `VALIDATION_ERROR` rõ field.
8. **Versioning** — nội bộ dùng `/internal/*`; nếu mở rộng sau này thêm `/v1` mà không phá đường cũ.
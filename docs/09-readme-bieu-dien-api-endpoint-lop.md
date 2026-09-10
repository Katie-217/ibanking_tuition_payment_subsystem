# 09 — README: Cách biểu diễn API trên frontend (Lớp Endpoint)

> Nguyên tắc số 1 của frontend dự án này:
> **KHÔNG BAO GIỜ viết URL trực tiếp trong code trang. Mọi đường dẫn API phải được khai báo
> tập trung trong `frontend/js/endpoints.js` và chỉ được gọi thông qua `API_ENDPOINTS` +
> `ApiClient`.**
>
> Lợi ích: khi backend sửa đường dẫn API, chỉ cần sửa **đúng 1 chỗ**; mọi trang vẫn chạy bình thường.

---

## 1. Kiến trúc gọi API 2 lớp

```
Trang HTML/JS (login.html, dashboard.html, history.html)
        │  chỉ dùng 2 đối tượng duy nhất:
        ▼
┌──────────────────────────────┐   ┌──────────────────────────────┐
│  endpoints.js (LỚP ENDPOINT) │   │  api-client.js (LỚP GỌI API)  │
│  - khai báo MỌI đường dẫn    │   │  - fetch + gắn Bearer token  │
│  - API_ENDPOINTS.auth.login  │──▶│  - parse lỗi envelope chuẩn  │
│  - API_ENDPOINTS.payments... │   │  - 401 → tự về trang login   │
└──────────────────────────────┘   └──────────────────────────────┘
        │ URL đầy đủ (API_BASE + path)
        ▼
   API Gateway :8000  →  các microservice
```

- **endpoints.js** chỉ trả lời câu hỏi: "đường dẫn này là gì?" — không gửi request.
- **api-client.js** chỉ lo "gửi request + xử lý token/lỗi" — không biết đường dẫn nào tồn tại.

---

## 2. Cấu trúc file `frontend/js/endpoints.js`

### 2.1 Base URL

```js
const API_BASE = (window.API_BASE_URL || "http://localhost:8000").replace(/\/+$/, "");
```

- Mặc định trỏ API Gateway cổng 8000.
- Muốn đổi môi trường (máy khác, server IOT…) — khai báo **trước** khi nạp file:

  ```html
  <script>window.API_BASE_URL = "http://192.168.1.10:8000";</script>
  <script src="js/api-client.js"></script>
  <script src="js/endpoints.js"></script>
  ```

### 2.2 Nhóm endpoint theo service

Cấu trúc: `API_ENDPOINTS.<nhóm>.<tên>` — nhóm trùng tên service:

| Nhóm trong code | Tương ứng service |
|---|---|
| `API_ENDPOINTS.auth` | auth-service :8001 |
| `API_ENDPOINTS.payers` | payer-service :8002 |
| `API_ENDPOINTS.tuition` | tuition-service :8003 |
| `API_ENDPOINTS.payments` | payment-service :8004 |
| `API_ENDPOINTS.health` | gateway /health |

### 2.3 Quy ước khai báo — 2 dạng

| Loại endpoint | Cách khai báo | Ví dụ |
|---|---|---|
| **Tĩnh** (không tham số) | **CHUỖI** | `me: \`${API_BASE}/payers/me\`` |
| **Động** (có path param) | **HÀM** nhận tham số | `detail: (paymentId) => \`${API_BASE}/payments/${encodeURIComponent(paymentId)}\`` |
| **Có query string** | hàm nhận object | `history: (q = {}) => \`${API_BASE}/payments${buildQuery(q)}\`` |

### 2.4 Toàn bộ danh sách đang khai báo (đồng bộ docs/11)

```js
const API_ENDPOINTS = Object.freeze({
  auth: Object.freeze({
    login:  `${API_BASE}/auth/login`,        // POST   {username, password}
    logout: `${API_BASE}/auth/logout`,       // POST   (Bearer JWT)
    me:     `${API_BASE}/auth/me`,           // GET    (Bearer JWT)
  }),
  payers: Object.freeze({
    me: `${API_BASE}/payers/me`,             // GET    (Bearer JWT)
  }),
  tuition: Object.freeze({
    me: `${API_BASE}/tuition/me`,            // GET    (Bearer JWT)
  }),
  payments: Object.freeze({
    create:    () => `${API_BASE}/payments`,                              // POST {tuition_id}
    detail:    (id) => `${API_BASE}/payments/${encodeURIComponent(id)}`,  // GET
    history:   (q = {}) => `${API_BASE}/payments${buildQuery(q)}`,        // GET ?status=&page=&size=
    verifyOtp: (id) => `${API_BASE}/payments/${encodeURIComponent(id)}/verify-otp`,  // POST {otp}
    resendOtp: (id) => `${API_BASE}/payments/${encodeURIComponent(id)}/resend-otp`,  // POST
    cancel:    (id) => `${API_BASE}/payments/${encodeURIComponent(id)}/cancel`,      // POST
  }),
  health: `${API_BASE}/health`,
});
```

Chi tiết tham số của từng API: xem [docs/11-tai-lieu-api-endpoint-resource.md](11-tai-lieu-api-endpoint-resource.md)
và spec đầy đủ [docs/03-thiet-ke-rest-api.md](03-thiet-ke-rest-api.md).

---

## 3. Cách dùng ở các trang — mẫu chuẩn

### 3.1 Đăng nhập

```js
// SAI  — tuyệt đối cấm:
// fetch("http://localhost:8000/auth/login", {...})

// ĐÚNG — luôn đi qua lớp endpoint:
try {
  const data = await ApiClient.post(API_ENDPOINTS.auth.login, {
    username: "521H0092",
    password: "abc12345",
  });
  ApiClient.setToken(data.token);          // tự lưu localStorage "ibanking_token"
  location.href = "dashboard.html";
} catch (e) {
  showError(e.code, e.message);            // e = {status, code, message, detail}
}
```

### 3.2 Nạp dữ liệu trang chính (gọi song song nhiều service)

```js
const [me, payer, tuition] = await Promise.all([
  ApiClient.get(API_ENDPOINTS.auth.me),
  ApiClient.get(API_ENDPOINTS.payers.me),
  ApiClient.get(API_ENDPOINTS.tuition.me),
]);
renderDashboard(me, payer, tuition);
```

### 3.3 Tạo giao dịch (có Idempotency-Key chống double-click)

```js
const key = ApiClient.newIdempotencyKey();   // sinh 1 lần cho cả thao tác
const { payment_id } = await ApiClient.post(
  API_ENDPOINTS.payments.create(),
  { tuition_id: 10 },
  { idempotencyKey: key }
);
gotoOtpScreen(payment_id);
```

### 3.4 Xác thực OTP

```js
try {
  const receipt = await ApiClient.post(
    API_ENDPOINTS.payments.verifyOtp(paymentId), { otp: "482913" }
  );
  showSuccessScreen(receipt);
} catch (e) {
  if (e.code === "OTP_EXPIRED") showResendButton();
  else showOtpError(e.code, e.message);
}
```

### 3.5 Lịch sử có query string

```js
const data = await ApiClient.get(
  API_ENDPOINTS.payments.history({ status: "SUCCESS", page: 1, size: 20 })
);
// gọi ra: GET /payments?status=SUCCESS&page=1&size=20
```

---

## 4. `ApiClient` xử lý hộ bạn những gì

| Việc | Cơ chế |
|---|---|
| Gắn token | tự đọc `localStorage.ibanking_token` → thêm header `Authorization: Bearer …` |
| Mã hóa body | nhận object → tự `JSON.stringify` + header `Content-Type: application/json` |
| Parse lỗi chuẩn | đọc envelope `{"error": {code, message, detail}}` → ném `Error` có `.status/.code/.detail` |
| Hết phiên (401) | tự xóa token + redirect `index.html` (trừ chính request login) |
| Chống ghi URL tay | ném lỗi nếu url không bắt đầu `http` — bắt buộc dùng `API_ENDPOINTS` |

## 5. Quy tắc khi thêm endpoint mới

1. Mở `frontend/js/endpoints.js`, tìm **đúng nhóm service**, thêm dòng theo đúng 2 dạng
   (chuỗi tĩnh / hàm động) ở mục 2.3 — kèm comment ghi method + body.
2. Cập nhật **cùng lúc** 2 tài liệu: [docs/11](11-tai-lieu-api-endpoint-resource.md) (thêm dòng
   vào bảng 3 cột) và [docs/03](03-thiet-ke-rest-api.md) (spec chi tiết).
3. Trang chỉ được gọi qua `API_ENDPOINTS.<nhóm>.<tên>`; nếu thấy chuỗi `fetch(`/`axios(`/URL
   viết tay xuất hiện trong code trang → đó là bug, phải sửa.
4. Đổi đường dẫn backend → sửa **duy nhất** trong `endpoints.js`; không đổi gì ở các trang.

## 6. Kiểm tra nhanh quy tắc trên browser

```js
// Mở console (F12) tại bất kỳ trang nào:
console.log(API_ENDPOINTS.payments.verifyOtp(42));   // http://localhost:8000/payments/42/verify-otp
console.log(API_ENDPOINTS.payments.history({status:"SUCCESS"})); // http://localhost:8000/payments?status=SUCCESS
```
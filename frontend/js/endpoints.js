/**
 * =====================================================================
 *  LỚP ENDPOINT — nơi khai báo DUY NHẤT mọi đường dẫn API của hệ thống.
 * =====================================================================
 *
 *  QUY TẮC BẮT BUỘC:
 *  1. Các trang HTML/JS KHÔNG BAO GIỜ viết URL trực tiếp trong code.
 *     - SAI  : fetch('/payers/me')
 *     - ĐÚNG : ApiClient.get(API_ENDPOINTS.payers.me)
 *
 *  2. Khi backend đổi đường dẫn API -> sửa ĐÚNG 1 CHỖ ở file này,
 *     toàn bộ trang vẫn chạy bình thường (quản lý tập trung).
 *
 *  3. Endpoint có tham số động (payment_id...) là HÀM : api(id),
 *     endpoint tĩnh là CHUỖI.
 *
 *  4. Base URL có thể ghi đè theo môi trường bằng cách khai báo
 *     window.API_BASE_URL trong <script> của index.html trước khi
 *     nạp file này:
 *         <script>window.API_BASE_URL = "http://192.168.1.10:8000";</script>
 * =====================================================================
 */

const API_BASE = (window.API_BASE_URL || "http://localhost:8000").replace(/\/+$/, "");

/** Hàm dựng query string: buildQuery({page: 1, status: "SUCCESS"}) -> "?page=1&status=SUCCESS" */
function buildQuery(params = {}) {
  const qs = Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== null && v !== "")
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
    .join("&");
  return qs ? `?${qs}` : "";
}

/** Danh sách endpoint — xem chi tiết từng API tại docs/03-thiet-ke-rest-api.md */
const API_ENDPOINTS = Object.freeze({

  // ------------------------- auth-service :8001 -------------------------
  auth: Object.freeze({
    login:  `${API_BASE}/auth/login`,   // POST   {username, password}
    logout: `${API_BASE}/auth/logout`,  // POST   (Bearer JWT)
    me:     `${API_BASE}/auth/me`,      // GET    (Bearer JWT)
  }),

  // ------------------------- payer-service :8002 ------------------------
  payers: Object.freeze({
    me: `${API_BASE}/payers/me`,        // GET    (Bearer JWT) -> thông tin người nộp + số dư
  }),

  // ------------------------- tuition-service :8003 ----------------------
  tuition: Object.freeze({
    /** GET /tuition/me — hồ sơ sinh viên + DANH SÁCH HỌC KỲ (số tiền, trạng thái, hạn nộp, ngày thanh toán) */
    me: `${API_BASE}/tuition/me`,

    /**
     * GET /tuitions/{id}/enrollments — CÁC MÔN đã đăng ký của học kỳ đó
     * (mã môn, tên môn, số tín chỉ, học phí từng môn) + thông tin người nhận cho popup.
     */
    enrollments: (tuitionId) =>
      `${API_BASE}/tuitions/${encodeURIComponent(tuitionId)}/enrollments`,
  }),

  // ------------------------- payment-service :8004 ----------------------
  payments: Object.freeze({
    /** POST /payments  — tạo giao dịch + gửi OTP. Body: {tuition_id} */
    create: (() => `${API_BASE}/payments`),

    /** GET /payments/{id} — chi tiết 1 giao dịch của mình */
    detail: (paymentId) => `${API_BASE}/payments/${encodeURIComponent(paymentId)}`,

    /** GET /payments — lịch sử giao dịch. Query: {status, page, size} */
    history: ((query = {}) => `${API_BASE}/payments${buildQuery(query)}`),

    /** POST /payments/{id}/verify-otp — xác thực OTP. Body: {otp} */
    verifyOtp: (paymentId) => `${API_BASE}/payments/${encodeURIComponent(paymentId)}/verify-otp`,

    /** POST /payments/{id}/resend-otp — gửi lại OTP */
    resendOtp: (paymentId) => `${API_BASE}/payments/${encodeURIComponent(paymentId)}/resend-otp`,

    /** POST /payments/{id}/cancel — hủy giao dịch đang chờ */
    cancel: (paymentId) => `${API_BASE}/payments/${encodeURIComponent(paymentId)}/cancel`,
  }),

  // ------------------------- hệ thống -----------------------------------
  health: `${API_BASE}/health`,         // GET    — trạng thái các service
});

// Hỗ trợ require() nếu chạy dưới Node (không bắt buộc cho browser)
if (typeof module !== "undefined" && module.exports) {
  module.exports = { API_BASE, API_ENDPOINTS, buildQuery };
}

/* =====================================================================
 *  CÁCH DÙNG Ở CÁC TRANG (ví dụ):
 *
 *  // Login
 *  const data = await ApiClient.post(API_ENDPOINTS.auth.login, {
 *      username: "521H0092", password: "abc12345"
 *  });
 *
 *  // Nạp trang thanh toán (trang chính sau khi đăng nhập)
 *  const [payer, tuition] = await Promise.all([
 *      ApiClient.get(API_ENDPOINTS.payers.me),
 *      ApiClient.get(API_ENDPOINTS.tuition.me),
 *  ]);
 *
 *  // Sinh viên chọn 1 học kỳ -> lấy các môn đã đăng ký + học phí từng môn
 *  const detail = await ApiClient.get(
 *      API_ENDPOINTS.tuition.enrollments(tuition.tuitions[0].tuition_id)
 *  );
 *  // detail.enrollments[] , detail.total_amount , detail.beneficiary
 *
 *  // Tạo giao dịch
 *  const { payment_id } = await ApiClient.post(API_ENDPOINTS.payments.create(), {
 *      tuition_id: tuition.tuitions[0].tuition_id
 *  });
 *
 *  // Xác thực OTP
 *  const receipt = await ApiClient.post(API_ENDPOINTS.payments.verifyOtp(payment_id), {
 *      otp: "123456"
 *  });
 * ===================================================================== */
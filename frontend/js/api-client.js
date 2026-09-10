/**
 * =====================================================================
 *  LỚP GỌI API TẬP TRUNG (ApiClient)
 * =====================================================================
 *
 *  - Mọi request trong dự án PHẢI đi qua lớp này, kết hợp với
 *    API_ENDPOINTS (file endpoints.js). Không được dùng fetch trực tiếp.
 *  - Tự động: gắn Authorization Bearer token, xử lý lỗi envelope chuẩn
 *    {"error": {"code", "message", "detail"}}, tự đăng xuất khi 401.
 * =====================================================================
 */

const ApiClient = (() => {
  const TOKEN_KEY = "ibanking_token";

  // ---------- quản lý token ----------
  const getToken    = () => localStorage.getItem(TOKEN_KEY);
  const setToken    = (token) =>
    token ? localStorage.setItem(TOKEN_KEY, token) : localStorage.removeItem(TOKEN_KEY);
  const clearToken  = () => localStorage.removeItem(TOKEN_KEY);

  // ---------- tiện ích ----------
  function buildHeaders(extra = {}) {
    const headers = { "Content-Type": "application/json", ...extra };
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
    return headers;
  }

  /**
   * Gửi request tới backend qua lớp endpoint.
   * @param {string} url      — đường dẫn lấy từ API_ENDPOINTS (KHÔNG viết tay)
   * @param {object} options  — {method, body, headers, idempotencyKey}
   * @returns {Promise<any>}  — dữ liệu JSON trả về
   * @throws  Error có {status, code, detail} khi backend báo lỗi
   */
  async function request(url, { method = "GET", body, headers = {}, idempotencyKey } = {}) {
    if (!url.startsWith("http")) {
      throw new Error("[ApiClient] Bắt buộc dùng đường dẫn lấy từ API_ENDPOINTS, không ghi URL tay.");
    }

    const finalHeaders = { ...headers };
    if (idempotencyKey) finalHeaders["Idempotency-Key"] = idempotencyKey;

    const res = await fetch(url, {
      method,
      headers: buildHeaders(finalHeaders),
      body: body !== undefined && body !== null ? JSON.stringify(body) : undefined,
    });

    const data = await res.json().catch(() => null);

    if (!res.ok) {
      // Phiên hết hạn -> xóa token, quay về trang login (trừ chính API login)
      if (res.status === 401 && !url.endsWith("/auth/login")) {
        clearToken();
        if (!location.pathname.endsWith("index.html")) location.href = "index.html";
      }

      const err = new Error(data?.error?.message || `Lỗi máy chủ (HTTP ${res.status})`);
      err.status = res.status;
      err.code   = data?.error?.code   || "UNKNOWN";
      err.detail = data?.error?.detail || null;
      throw err;
    }
    return data;
  }

  // ---------- API công khai ----------
  return {
    get:  (url, opts = {}) => request(url, { ...opts, method: "GET" }),
    post: (url, body, opts = {}) => request(url, { ...opts, method: "POST", body }),

    /** Idempotency: tạo key ngẫu nhiên dùng 1 lần khi tạo giao dịch (chống double-click) */
    newIdempotencyKey: () =>
      (crypto.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(36).slice(2)}`),

    getToken, setToken, clearToken,
  };
})();

// Hỗ trợ require() nếu chạy dưới Node (không bắt buộc cho browser)
if (typeof module !== "undefined" && module.exports) {
  module.exports = { ApiClient };
}

/* =====================================================================
 *  CÁCH DÙNG (tích hợp với endpoints.js):
 *
 *  const payer = await ApiClient.get(API_ENDPOINTS.payers.me);
 *  const result = await ApiClient.post(
 *      API_ENDPOINTS.payments.create(),
 *      { tuition_id: 10 },
 *      { idempotencyKey: ApiClient.newIdempotencyKey() }
 *  );
 *
 *  // Bắt lỗi nghiệp vụ để hiển thị đúng message:
 *  try {
 *      await ApiClient.post(API_ENDPOINTS.payments.verifyOtp(42), { otp });
 *  } catch (e) {
 *      showError(e.code, e.message);   // ví dụ OTP_EXPIRED ...
 *  }
 * ===================================================================== */
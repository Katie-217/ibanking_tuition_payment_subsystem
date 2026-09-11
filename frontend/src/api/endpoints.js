const API_BASE = (import.meta.env.VITE_API_BASE || "http://localhost:8000").replace(/\/+$/, "");

function buildQuery(params = {}) {
  const qs = Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== null && v !== "")
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
    .join("&");
  return qs ? `?${qs}` : "";
}

export const API_ENDPOINTS = Object.freeze({
  auth: Object.freeze({
    login: `${API_BASE}/auth/login`,
    logout: `${API_BASE}/auth/logout`,
    me: `${API_BASE}/auth/me`,
  }),
  payers: Object.freeze({
    me: `${API_BASE}/payers/me`,
  }),
  tuition: Object.freeze({
    me: `${API_BASE}/tuition/me`,
    enrollments: (tuitionId) =>
      `${API_BASE}/tuitions/${encodeURIComponent(tuitionId)}/enrollments`,
  }),
  payments: Object.freeze({
    create: () => `${API_BASE}/payments`,
    detail: (paymentId) => `${API_BASE}/payments/${encodeURIComponent(paymentId)}`,
    history: (query = {}) => `${API_BASE}/payments${buildQuery(query)}`,
    verifyOtp: (paymentId) =>
      `${API_BASE}/payments/${encodeURIComponent(paymentId)}/verify-otp`,
    resendOtp: (paymentId) =>
      `${API_BASE}/payments/${encodeURIComponent(paymentId)}/resend-otp`,
    cancel: (paymentId) =>
      `${API_BASE}/payments/${encodeURIComponent(paymentId)}/cancel`,
  }),
  health: `${API_BASE}/health`,
});

export { API_BASE, buildQuery };

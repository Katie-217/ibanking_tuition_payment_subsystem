import { API_ENDPOINTS } from "./endpoints";

const TOKEN_KEY = "ibanking_token";

export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const setToken = (token) =>
  token ? localStorage.setItem(TOKEN_KEY, token) : localStorage.removeItem(TOKEN_KEY);
export const clearToken = () => localStorage.removeItem(TOKEN_KEY);

export const newIdempotencyKey = () =>
  crypto.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(36).slice(2)}`;

let onUnauthorized = () => {};
export function setUnauthorizedHandler(fn) {
  onUnauthorized = fn;
}

function buildHeaders(extra = {}) {
  const headers = { "Content-Type": "application/json", ...extra };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  return headers;
}

export async function request(url, { method = "GET", body, headers = {}, idempotencyKey } = {}) {
  if (!url.startsWith("http")) {
    throw new Error("Phải dùng đường dẫn từ API_ENDPOINTS, không ghi URL trực tiếp");
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
    if (res.status === 401 && !url.endsWith("/auth/login")) {
      clearToken();
      onUnauthorized();
    }
    const err = new Error(data?.error?.message || `Lỗi máy chủ (HTTP ${res.status})`);
    err.status = res.status;
    err.code = data?.error?.code || "UNKNOWN";
    err.detail = data?.error?.detail || null;
    throw err;
  }
  return data;
}

export const ApiClient = {
  get: (url, opts = {}) => request(url, { ...opts, method: "GET" }),
  post: (url, body, opts = {}) => request(url, { ...opts, method: "POST", body }),
  getToken,
  setToken,
  clearToken,
  newIdempotencyKey,
};

export { API_ENDPOINTS };

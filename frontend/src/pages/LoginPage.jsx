import { useState } from "react";
import { useNavigate, Navigate } from "react-router-dom";
import { ApiClient, API_ENDPOINTS, getToken } from "../api/client.js";

const MSSV_RE = /^\d{3}[A-Za-z]\d{4}$/;

const ERROR_MESSAGES = {
  VALIDATION_ERROR: "Mã số sinh viên không đúng định dạng (VD: 521H0092)",
  AUTH_INVALID_CREDENTIALS: "Sai mã số sinh viên hoặc mật khẩu",
  FORBIDDEN: "Tài khoản đã bị khóa",
  SERVICE_UNAVAILABLE: "Máy chủ đang bận, vui lòng thử lại sau",
};

export default function LoginPage() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [fieldError, setFieldError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  if (getToken()) return <Navigate to="/" replace />;

  function validateUsername(value) {
    if (!value) return "Vui lòng nhập mã số sinh viên";
    if (!MSSV_RE.test(value)) return "MSSV gồm 3 số + 1 chữ + 4 số (VD: 521H0092)";
    return "";
  }

  function onUsernameChange(e) {
    setUsername(e.target.value);
    if (fieldError) setFieldError("");
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    const uErr = validateUsername(username);
    setFieldError(uErr);
    if (uErr) return;
    if (!password) {
      setError("Vui lòng nhập mật khẩu");
      return;
    }

    setSubmitting(true);
    try {
      const data = await ApiClient.post(API_ENDPOINTS.auth.login, {
        username: username.toUpperCase(),
        password,
      });
      ApiClient.setToken(data.token);
      navigate("/", { replace: true });
    } catch (err) {
      setError(ERROR_MESSAGES[err.code] || err.message || "Đăng nhập thất bại");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="login-bg">
      <form className="login-card" onSubmit={handleSubmit} noValidate>
        <div className="login-logo">
          <span className="brand-mark brand-mark-lg">iB</span>
        </div>
        <h1>iBanking</h1>
        <p className="login-sub">Thanh toán học phí trực tuyến — TDTU</p>

        <label className="field">
          <span>Mã số sinh viên</span>
          <input
            value={username}
            onChange={onUsernameChange}
            placeholder="521H0092"
            autoComplete="username"
            autoFocus
            className={fieldError ? "input-error" : ""}
          />
          {fieldError && <small className="field-error">{fieldError}</small>}
        </label>

        <label className="field">
          <span>Mật khẩu</span>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            autoComplete="current-password"
          />
        </label>

        {error && <div className="alert alert-error">{error}</div>}

        <button type="submit" className="btn btn-primary btn-block" disabled={submitting}>
          {submitting ? "Đang đăng nhập…" : "Đăng nhập"}
        </button>

        <p className="login-hint">Tài khoản demo: 521H0092 / 522H0145 / 523H0201 — mật khẩu abc12345</p>
      </form>
    </div>
  );
}

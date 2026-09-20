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
  const [username, setUsername] = useState("521H0092");
  const [password, setPassword] = useState("Password123@");
  const [showPassword, setShowPassword] = useState(false);
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
    <div className="tdtu-login-bg">
      <div className="tdtu-login-card">
        {/* PANEL TRÁI - RED BRAND PANEL */}
        <div className="tdtu-left-panel">
          <div className="tdtu-logo-box">
            <img src="/logo.png" alt="TDTU Logo" className="tdtu-logo-img" />
          </div>
          
          <div className="tdtu-title-group">
            <h1>CỔNG</h1>
            <h1>THANH TOÁN</h1>
            <h1>SINH VIÊN</h1>
          </div>

          <div className="tdtu-badge-overlap">
            <div className="tdtu-badge-inner">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="2" y="5" width="20" height="14" rx="2" />
                <line x1="2" y1="10" x2="22" y2="10" />
              </svg>
            </div>
          </div>
        </div>

        {/* PANEL PHẢI - WHITE FORM PANEL */}
        <div className="tdtu-right-panel">
          <div className="tdtu-welcome-header">
            <h2>XIN CHÀO!</h2>
          </div>

          <form onSubmit={handleSubmit} noValidate className="tdtu-form">
            <div className="tdtu-input-group">
              <span className="tdtu-input-icon red-icon">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
                </svg>
              </span>
              <input
                value={username}
                onChange={onUsernameChange}
                placeholder="Mã số sinh viên (VD: 521H0092)"
                autoComplete="username"
                autoFocus
                className={fieldError ? "input-error" : ""}
              />
            </div>
            {fieldError && <div className="tdtu-field-error">{fieldError}</div>}

            <div className="tdtu-input-group">
              <span className="tdtu-input-icon dark-icon">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M18 8h-1V6c0-2.76-2.24-5-5-5S7 3.24 7 6v2H6c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V10c0-1.1-.9-2-2-2zm-6 9c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2zm3.1-9H8.9V6c0-1.71 1.39-3.1 3.1-3.1 1.71 0 3.1 1.39 3.1 3.1v2z"/>
                </svg>
              </span>
              <input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Mật khẩu"
                autoComplete="current-password"
              />
              <button
                type="button"
                className="tdtu-eye-toggle"
                onClick={() => setShowPassword(!showPassword)}
                title={showPassword ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  {showPassword ? (
                    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24M1 1l22 22"/>
                  ) : (
                    <>
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                      <circle cx="12" cy="12" r="3" />
                    </>
                  )}
                </svg>
              </button>
            </div>

            {error && <div className="tdtu-alert-error">{error}</div>}

            <div className="tdtu-btn-container">
              <button type="submit" className="tdtu-btn-submit" disabled={submitting}>
                {submitting ? "ĐANG ĐĂNG NHẬP..." : "ĐĂNG NHẬP"}
              </button>
            </div>
          </form>

          {/* HINT CỦA DỰ ÁN */}
          <div className="tdtu-demo-hint">
            <strong>Tài khoản thử nghiệm:</strong> <code>521H0092</code> / <code>523H0058</code> — Mật khẩu: <code>Password123@</code>
          </div>
        </div>
      </div>
    </div>
  );
}

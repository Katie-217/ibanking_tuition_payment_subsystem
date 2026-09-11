import { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ApiClient, API_ENDPOINTS } from "../api/client.js";

const money = new Intl.NumberFormat("vi-VN");

function fmtTime(seconds) {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

const VERIFY_MESSAGES = {
  OTP_INVALID: "Mã OTP không đúng",
  OTP_EXPIRED: "Mã OTP đã hết hạn — bấm Gửi lại mã để nhận mã mới",
  OTP_USED: "Mã OTP đã được sử dụng — bấm Gửi lại mã",
  OTP_LOCKED: "Nhập sai quá 5 lần — giao dịch đã bị hủy, học phí được mở khóa",
  INSUFFICIENT_BALANCE: "Số dư không đủ — giao dịch đã kết thúc",
  PAYMENT_CONFLICT_CONCURRENT: "Học phí vừa được thanh toán bởi giao dịch khác — tiền đã hoàn lại",
  STATE_CONFLICT: "Giao dịch không còn hiệu lực",
};

export default function OtpPage() {
  const { paymentId } = useParams();
  const navigate = useNavigate();
  const [payment, setPayment] = useState(null);
  const [loadError, setLoadError] = useState("");
  const [otp, setOtp] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [success, setSuccess] = useState(null);
  const [busy, setBusy] = useState(false);
  const [remainSec, setRemainSec] = useState(0);
  const [resendIn, setResendIn] = useState(30);
  const [confirmCancel, setConfirmCancel] = useState(false);
  const inputRef = useRef(null);

  const loadPayment = useCallback(async () => {
    try {
      const p = await ApiClient.get(API_ENDPOINTS.payments.detail(paymentId));
      setPayment(p);
      return p;
    } catch (err) {
      setLoadError(err.message);
      return null;
    }
  }, [paymentId]);

  useEffect(() => {
    loadPayment().then((p) => {
      if (p && p.status === "OTP_SENT") inputRef.current?.focus();
    });
  }, [loadPayment]);

  useEffect(() => {
    if (!payment || payment.status !== "OTP_SENT") return;
    const tick = () => {
      const end = new Date(payment.expires_at).getTime();
      const left = Math.floor((end - Date.now()) / 1000);
      setRemainSec(Math.max(0, left));
    };
    tick();
    const timer = setInterval(tick, 1000);
    return () => clearInterval(timer);
  }, [payment]);

  useEffect(() => {
    if (resendIn <= 0) return;
    const timer = setInterval(() => setResendIn((v) => Math.max(0, v - 1)), 1000);
    return () => clearInterval(timer);
  }, [resendIn]);

  async function handleVerify(e) {
    e.preventDefault();
    setError("");
    setNotice("");
    if (!/^\d{6}$/.test(otp)) {
      setError("Mã OTP gồm đúng 6 chữ số");
      return;
    }
    setBusy(true);
    try {
      const result = await ApiClient.post(API_ENDPOINTS.payments.verifyOtp(paymentId), { otp });
      setSuccess(result);
    } catch (err) {
      setError(VERIFY_MESSAGES[err.code] || err.message);
      if (err.detail) setError((prev) => `${prev} (${err.detail})`);
      if (["OTP_LOCKED", "INSUFFICIENT_BALANCE", "PAYMENT_CONFLICT_CONCURRENT"].includes(err.code)) {
        await loadPayment();
      }
    } finally {
      setBusy(false);
    }
  }

  async function handleResend() {
    setError("");
    setNotice("");
    setBusy(true);
    try {
      await ApiClient.post(API_ENDPOINTS.payments.resendOtp(paymentId));
      setOtp("");
      setResendIn(30);
      setNotice("Đã gửi mã mới, vui lòng kiểm tra email");
      inputRef.current?.focus();
      await loadPayment();
    } catch (err) {
      if (err.code === "RATE_LIMITED") {
        setError(err.message);
        setResendIn(30);
      } else {
        setError(err.code === "STATE_CONFLICT" ? "Giao dịch không còn hiệu lực để gửi lại mã" : err.message);
        await loadPayment();
      }
    } finally {
      setBusy(false);
    }
  }

  async function handleCancel() {
    setBusy(true);
    setError("");
    try {
      await ApiClient.post(API_ENDPOINTS.payments.cancel(paymentId));
      navigate("/", { replace: true });
    } catch (err) {
      setError(err.message);
      await loadPayment();
      setConfirmCancel(false);
      setBusy(false);
    }
  }

  if (loadError) {
    return (
      <div className="page">
        <div className="alert alert-error">{loadError}</div>
        <button className="btn btn-outline" onClick={() => navigate("/")}>Về trang chủ</button>
      </div>
    );
  }

  if (!payment) {
    return (
      <div className="page">
        <div className="skeleton skeleton-card" />
      </div>
    );
  }

  if (success) {
    return (
      <div className="page page-narrow">
        <div className="card card-success">
          <div className="success-icon">✓</div>
          <h2>Thanh toán thành công</h2>
          <div className="receipt">
            <div className="receipt-row"><span>Mã giao dịch</span><strong>#{success.payment_id}</strong></div>
            <div className="receipt-row"><span>Số tiền</span><strong>{money.format(success.amount)} ₫</strong></div>
            <div className="receipt-row"><span>Sinh viên</span><strong>{success.student?.student_id} — {success.student?.full_name}</strong></div>
            <div className="receipt-row"><span>Số dư còn lại</span><strong>{money.format(success.balance_after)} ₫</strong></div>
          </div>
          <p className="muted">Email xác nhận đã gửi tới bạn và nhà trường.</p>
          <button className="btn btn-primary btn-block" onClick={() => navigate("/", { replace: true })}>
            Về trang chủ
          </button>
        </div>
      </div>
    );
  }

  const active = payment.status === "OTP_SENT";
  const expiredByJob = ["EXPIRED", "CANCELLED", "FAILED", "SUCCESS"].includes(payment.status);
  const remainMinutes = Math.floor(remainSec / 60);

  if (!active) {
    const statusText = {
      EXPIRED: "Giao dịch đã hết hạn — học phí được mở khóa, bạn có thể thanh toán lại",
      CANCELLED: "Giao dịch đã được hủy — học phí được mở khóa",
      FAILED: `Giao dịch thất bại (${payment.failure_reason || "không rõ lý do"}) — học phí được mở khóa`,
      PROCESSING: "Giao dịch đang được xử lý…",
      PENDING: "Giao dịch đang khởi tạo…",
    };
    return (
      <div className="page page-narrow">
        <div className="card">
          <h2>{statusText[payment.status] || `Trạng thái: ${payment.status}`}</h2>
          <div className="receipt">
            <div className="receipt-row"><span>Mã giao dịch</span><strong>#{payment.payment_id}</strong></div>
            <div className="receipt-row"><span>Số tiền</span><strong>{money.format(payment.amount)} ₫</strong></div>
          </div>
          <button className="btn btn-primary btn-block" onClick={() => navigate("/", { replace: true })}>
            Về trang chủ
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="page page-narrow">
      <div className="card card-otp">
        <h2>Xác thực OTP</h2>
        <div className="receipt">
          <div className="receipt-row"><span>Mã giao dịch</span><strong>#{payment.payment_id}</strong></div>
          <div className="receipt-row"><span>Học phí</span><strong>#{payment.tuition_id}</strong></div>
          <div className="receipt-row"><span>Số tiền</span><strong className="amount">{money.format(payment.amount)} ₫</strong></div>
        </div>

        <div className={`otp-timer ${remainSec <= 60 ? "timer-warn" : ""}`}>
          {remainSec > 0 ? (
            <>Giao dịch còn hiệu lực: <strong>{fmtTime(remainSec)}</strong></>
          ) : (
            <>Đang hết hạn… hệ thống sẽ tự động kết thúc giao dịch</>
          )}
        </div>

        <form onSubmit={handleVerify}>
          <label className="field">
            <span>Mã OTP (6 chữ số, gửi qua email)</span>
            <input
              ref={inputRef}
              value={otp}
              onChange={(e) => setOtp(e.target.value.replace(/\D/g, "").slice(0, 6))}
              placeholder="••••••"
              inputMode="numeric"
              maxLength={6}
              className="otp-input"
              autoComplete="one-time-code"
            />
          </label>

          {error && <div className="alert alert-error">{error}</div>}
          {notice && <div className="alert alert-ok">{notice}</div>}

          <div className="otp-actions">
            <button type="submit" className="btn btn-primary btn-block" disabled={busy || otp.length !== 6}>
              {busy ? "Đang xử lý…" : "Xác nhận thanh toán"}
            </button>
          </div>
        </form>

        <div className="otp-secondary">
          {resendIn > 0 ? (
            <span className="muted">Gửi lại mã sau {resendIn}s</span>
          ) : (
            <button className="btn btn-outline" onClick={handleResend} disabled={busy}>
              Gửi lại mã
            </button>
          )}
          <button className="btn btn-danger-ghost" onClick={() => setConfirmCancel(true)} disabled={busy}>
            Hủy giao dịch
          </button>
        </div>
        <p className="muted small">Mã có hiệu lực {remainMinutes > 0 ? `${remainMinutes} phút` : "ít hơn 1 phút"} và chỉ dùng 1 lần. Nhập sai quá 5 lần giao dịch sẽ bị hủy.</p>
      </div>

      {confirmCancel && (
        <div className="modal-backdrop" onClick={() => setConfirmCancel(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>Hủy giao dịch?</h3>
            <p>Giao dịch <strong>{money.format(payment.amount)} ₫</strong> cho học phí #{payment.tuition_id} sẽ bị hủy và học phí được mở khóa.</p>
            <div className="modal-actions">
              <button className="btn btn-outline" onClick={() => setConfirmCancel(false)}>Đóng</button>
              <button className="btn btn-danger" onClick={handleCancel} disabled={busy}>
                {busy ? "Đang hủy…" : "Xác nhận hủy"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

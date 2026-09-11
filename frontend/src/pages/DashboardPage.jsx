import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { ApiClient, API_ENDPOINTS, newIdempotencyKey } from "../api/client.js";

const money = new Intl.NumberFormat("vi-VN");

const STATUS_BADGE = {
  UNPAID: { label: "Chưa nộp", cls: "badge-red" },
  PAYING: { label: "Đang thanh toán", cls: "badge-orange" },
  PAID: { label: "Đã nộp", cls: "badge-green" },
};

function fmtDate(value) {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString("vi-VN");
}

export default function DashboardPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [payer, setPayer] = useState(null);
  const [tuition, setTuition] = useState(null);
  const [paying, setPaying] = useState(null);
  const [payError, setPayError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError("");
    try {
      const [payerData, tuitionData] = await Promise.all([
        ApiClient.get(API_ENDPOINTS.payers.me),
        ApiClient.get(API_ENDPOINTS.tuition.me),
      ]);
      setPayer(payerData);
      setTuition(tuitionData);
    } catch (err) {
      setLoadError(err.message || "Không tải được dữ liệu");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function handlePay(t) {
    setPayError("");
    setPaying(t.tuition_id);
    try {
      const result = await ApiClient.post(
        API_ENDPOINTS.payments.create(),
        { tuition_id: t.tuition_id },
        { idempotencyKey: newIdempotencyKey() }
      );
      navigate(`/pay/${result.payment_id}`);
    } catch (err) {
      const messages = {
        TUITION_ALREADY_PAID: "Khoản học phí này đã được thanh toán",
        PAYMENT_ALREADY_ACTIVE: "Bạn đang có giao dịch chưa hoàn tất — vui lòng xử lý xong mới tạo giao dịch mới",
        STATE_CONFLICT: "Học phí đang được thanh toán bởi giao dịch khác",
        SERVICE_UNAVAILABLE: "Hệ thống đang bận, vui lòng thử lại sau",
      };
      setPayError(messages[err.code] || err.message);
      setPaying(null);
    }
  }

  if (loading) {
    return (
      <div className="page">
        <div className="skeleton skeleton-title" />
        <div className="cards">
          <div className="skeleton skeleton-card" />
          <div className="skeleton skeleton-card" />
        </div>
        <div className="skeleton skeleton-table" />
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="page">
        <div className="alert alert-error">
          {loadError}
          <button className="btn btn-outline" onClick={load}>Thử lại</button>
        </div>
      </div>
    );
  }

  const s = tuition.student;
  const tuitions = tuition.tuitions || [];

  return (
    <div className="page">
      <h2 className="page-title">Hồ sơ sinh viên</h2>

      <div className="cards">
        <div className="card card-profile">
          <div className="profile-head">
            <div className="avatar avatar-lg">{(s.full_name || "?").trim().charAt(0).toUpperCase()}</div>
            <div>
              <div className="profile-name">{s.full_name}</div>
              <div className="profile-id">{s.student_id} · Khóa {s.enrollment_year}</div>
            </div>
          </div>
          <div className="info-grid">
            <div className="info-item">
              <span className="info-label">Trường</span>
              <span className="info-value">{s.school?.name}</span>
            </div>
            <div className="info-item">
              <span className="info-label">Khoa</span>
              <span className="info-value">{s.faculty?.name} <small>({s.faculty?.code})</small></span>
            </div>
            <div className="info-item">
              <span className="info-label">Ngành</span>
              <span className="info-value">{s.major?.name} <small>({s.major?.code})</small></span>
            </div>
            <div className="info-item">
              <span className="info-label">Hệ đào tạo</span>
              <span className="info-value">{s.edu_system?.name} <small>({s.edu_system?.code})</small></span>
            </div>
          </div>
        </div>

        <div className="card card-balance">
          <span className="info-label">Số dư khả dụng</span>
          <div className="balance-value">{money.format(payer.available_balance)} ₫</div>
          <div className="balance-sub">Tài khoản: {payer.payer_uid} · {payer.email}</div>
        </div>
      </div>

      <h2 className="page-title">Học phí theo học kỳ</h2>
      {payError && <div className="alert alert-error">{payError}</div>}

      {tuitions.length === 0 ? (
        <div className="empty">Chưa có khoản học phí nào</div>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>Học kỳ</th>
              <th className="col-money">Số tiền</th>
              <th>Hạn nộp</th>
              <th>Trạng thái</th>
              <th className="col-action">Thao tác</th>
            </tr>
          </thead>
          <tbody>
            {tuitions.map((t) => {
              const badge = STATUS_BADGE[t.status] || { label: t.status, cls: "badge-gray" };
              return (
                <tr key={t.tuition_id}>
                  <td className="cell-strong">{t.semester}</td>
                  <td className="col-money">{money.format(t.amount)} ₫</td>
                  <td>{fmtDate(t.due_date)}</td>
                  <td>
                    <span className={`badge ${badge.cls}`}>{badge.label}</span>
                    {t.status === "PAID" && t.paid_at && (
                      <small className="paid-date"> · {fmtDate(t.paid_at)}</small>
                    )}
                  </td>
                  <td className="col-action">
                    {t.status === "UNPAID" ? (
                      <button
                        className="btn btn-primary btn-sm"
                        disabled={paying !== null}
                        onClick={() => handlePay(t)}
                      >
                        {paying === t.tuition_id ? "Đang tạo…" : "Thanh toán"}
                      </button>
                    ) : (
                      <span className="muted">—</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}

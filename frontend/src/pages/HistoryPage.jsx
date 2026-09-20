import { useState, useEffect, useCallback } from "react";
import { ApiClient, API_ENDPOINTS } from "../api/client.js";

const money = new Intl.NumberFormat("vi-VN");

const FILTERS = [
  { key: "", label: "Tất cả" },
  { key: "PENDING,OTP_SENT,PROCESSING", label: "Đang chờ" },
  { key: "SUCCESS", label: "Thành công" },
  { key: "FAILED", label: "Thất bại" },
  { key: "CANCELLED", label: "Đã hủy" },
  { key: "EXPIRED", label: "Hết hạn" },
];

const STATUS_BADGE = {
  PENDING: { label: "Khởi tạo", cls: "badge-gray" },
  OTP_SENT: { label: "Chờ OTP", cls: "badge-yellow" },
  PROCESSING: { label: "Đang xử lý", cls: "badge-blue" },
  SUCCESS: { label: "Thành công", cls: "badge-green" },
  FAILED: { label: "Thất bại", cls: "badge-red" },
  CANCELLED: { label: "Đã hủy", cls: "badge-darkgray" },
  EXPIRED: { label: "Hết hạn", cls: "badge-purple" },
};

const FAILURE_LABELS = {
  OTP_LOCKED: "Nhập sai OTP quá 5 lần",
  CAPTURE_INSUFFICIENT_BALANCE: "Số dư không đủ",
  TUITION_PAID_STATE_CONFLICT: "Học phí được thanh toán bởi giao dịch khác",
  NGUOI_DUNG_HUY: "Người dùng hủy",
  LOCK_TUITION_STATE_CONFLICT: "Học phí bị khóa bởi giao dịch khác",
};

function fmtDateTime(value) {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString("vi-VN");
}

export default function HistoryPage() {
  const [filter, setFilter] = useState("");
  const [page, setPage] = useState(1);
  const [size] = useState(10);
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [detail, setDetail] = useState(null);
  const [detailError, setDetailError] = useState("");

  const totalPages = Math.max(1, Math.ceil(total / size));

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError("");
    try {
      const statuses = filter ? filter.split(",") : [""];
      const results = await Promise.all(
        statuses.map((status) =>
          ApiClient.get(API_ENDPOINTS.payments.history({ status: status || undefined, page, size }))
        )
      );
      if (statuses.length === 1) {
        setItems(results[0].items);
        setTotal(results[0].total);
      } else {
        const merged = results
          .flatMap((r) => r.items)
          .sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
        setItems(merged.slice(0, size));
        setTotal(results.reduce((sum, r) => sum + r.total, 0));
      }
    } catch (err) {
      setLoadError(err.message);
    } finally {
      setLoading(false);
    }
  }, [filter, page, size]);

  useEffect(() => {
    load();
  }, [load]);

  async function openDetail(p) {
    setDetailError("");
    setDetail(null);
    try {
      const d = await ApiClient.get(API_ENDPOINTS.payments.detail(p.payment_id));
      setDetail(d);
    } catch (err) {
      setDetailError(err.message);
    }
  }

  return (
    <div className="page">
      <h2 className="page-title">Lịch sử giao dịch</h2>

      <div className="chip-row">
        {FILTERS.map((f) => (
          <button
            key={f.key || "all"}
            className={`chip ${filter === f.key ? "chip-active" : ""}`}
            onClick={() => {
              setFilter(f.key);
              setPage(1);
            }}
          >
            {f.label}
          </button>
        ))}
      </div>

      {loadError && (
        <div className="alert alert-error">
          {loadError}
          <button className="btn btn-outline" onClick={load}>Thử lại</button>
        </div>
      )}

      {loading ? (
        <div className="skeleton skeleton-table" />
      ) : items.length === 0 ? (
        <div className="empty">Chưa có giao dịch nào</div>
      ) : (
        <>
          <table className="table table-click">
            <thead>
              <tr>
                <th>Mã GD</th>
                <th>Ngày tạo</th>
                <th>Học phí</th>
                <th className="col-money">Số tiền</th>
                <th>Trạng thái</th>
              </tr>
            </thead>
            <tbody>
              {items.map((p) => {
                const badge = STATUS_BADGE[p.status] || { label: p.status, cls: "badge-gray" };
                return (
                  <tr key={p.payment_id} onClick={() => openDetail(p)}>
                    <td className="cell-strong">#{p.payment_id}</td>
                    <td>{fmtDateTime(p.created_at)}</td>
                    <td>#{p.tuition_id}</td>
                    <td className="col-money">{money.format(p.amount)} ₫</td>
                    <td><span className={`badge ${badge.cls}`}>{badge.label}</span></td>
                  </tr>
                );
              })}
            </tbody>
          </table>

          <div className="pager">
            <button className="btn btn-outline btn-sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
              ← Trước
            </button>
            <span>Trang {page}/{totalPages} · {total} giao dịch</span>
            <button className="btn btn-outline btn-sm" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
              Sau →
            </button>
          </div>
        </>
      )}

      {(detail || detailError) && (
        <div className="modal-backdrop" onClick={() => { setDetail(null); setDetailError(""); }}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            {detailError ? (
              <>
                <h3>Không tải được chi tiết</h3>
                <p>{detailError}</p>
              </>
            ) : detail ? (
              <>
                <h3>Giao dịch #{detail.payment_id}</h3>
                <div className="receipt">
                  <div className="receipt-row">
                    <span>Trạng thái</span>
                    <span className={`badge ${STATUS_BADGE[detail.status]?.cls || "badge-gray"}`}>
                      {STATUS_BADGE[detail.status]?.label || detail.status}
                    </span>
                  </div>
                  <div className="receipt-row"><span>Số tiền</span><strong>{money.format(detail.amount)} ₫</strong></div>
                  <div className="receipt-row"><span>Sinh viên</span><strong>{detail.student_id}</strong></div>
                  <div className="receipt-row"><span>Học phí</span><strong>#{detail.tuition_id}</strong></div>
                  <div className="receipt-row"><span>Ngày tạo</span><strong>{fmtDateTime(detail.created_at)}</strong></div>
                  {detail.completed_at && (
                    <div className="receipt-row"><span>Hoàn tất</span><strong>{fmtDateTime(detail.completed_at)}</strong></div>
                  )}
                  {detail.failure_reason && (
                    <div className="receipt-row">
                      <span>Lý do kết thúc</span>
                      <strong>{FAILURE_LABELS[detail.failure_reason] || detail.failure_reason}</strong>
                    </div>
                  )}
                </div>

                {detail.status === "SUCCESS" && (
                  <p className="alert alert-ok slim">✓ Đã gửi email xác nhận cho sinh viên và nhà trường</p>
                )}

                {detail.history?.length > 0 && (
                  <div className="timeline">
                    {detail.history.map((h, i) => (
                      <div className="timeline-item" key={i}>
                        <span className="timeline-dot" />
                        <div>
                          <div className="timeline-label">
                            {h.from_status ? `${h.from_status} → ${h.to_status}` : h.to_status}
                          </div>
                          {h.note && <div className="timeline-note">{h.note}</div>}
                          <div className="timeline-time">{fmtDateTime(h.at)}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </>
            ) : null}
            <div className="modal-actions">
              <button className="btn btn-outline" onClick={() => { setDetail(null); setDetailError(""); }}>Đóng</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

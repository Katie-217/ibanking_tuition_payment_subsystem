import { useState, useEffect, useCallback } from "react";
import { useNavigate, useOutletContext } from "react-router-dom";
import { ApiClient, API_ENDPOINTS, newIdempotencyKey } from "../api/client.js";

const money = new Intl.NumberFormat("vi-VN");

function fmtDate(value) {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString("vi-VN");
}

export default function DashboardPage() {
  const navigate = useNavigate();
  const outletContext = useOutletContext() || {};
  const { topTab } = outletContext;

  const [loading, setLoading] = useState(!outletContext.tuition);
  const [loadError, setLoadError] = useState("");
  const [payerData, setPayerData] = useState(outletContext.payer || null);
  const [tuitionData, setTuitionData] = useState(outletContext.tuition || null);
  const [meData, setMeData] = useState(outletContext.me || null);
  const [paymentHistory, setPaymentHistory] = useState([]);
  const [paying, setPaying] = useState(null);
  const [payError, setPayError] = useState("");

  const [selectedSemester, setSelectedSemester] = useState("Học kỳ 1/ 2026 - 2027");
  const [activeSubTab, setActiveSubTab] = useState("tuition"); // 'tuition' | 'payment'

  const loadAll = useCallback(async () => {
    setLoading(true);
    setLoadError("");
    try {
      const [mRes, pRes, tRes, historyRes] = await Promise.all([
        ApiClient.get(API_ENDPOINTS.auth.me).catch(() => null),
        ApiClient.get(API_ENDPOINTS.payers.me).catch(() => null),
        ApiClient.get(API_ENDPOINTS.tuition.me).catch(() => null),
        ApiClient.get(API_ENDPOINTS.payments.history({ status: "SUCCESS", page: 1, size: 10 })).catch(() => ({ items: [] })),
      ]);

      if (mRes) setMeData(mRes);
      if (pRes) setPayerData(pRes);
      if (tRes) setTuitionData(tRes);
      if (historyRes?.items) setPaymentHistory(historyRes.items);
    } catch (err) {
      setLoadError(err.message || "Không tải được dữ liệu học phí");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  // Handle tuition payment
  async function handlePay(t) {
    if (!t) return;
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

  const tuitions = tuitionData?.tuitions || [];
  const s = tuitionData?.student || {};

  // Match selected semester or fall back to first item
  const activeTuition =
    tuitions.find((t) => t.semester === selectedSemester || `${t.semester}/ 2026 - 2027` === selectedSemester) ||
    tuitions[0] ||
    null;

  const items = activeTuition?.items || [];
  const isPaid = activeTuition?.status === "PAID";
  const tuitionAmount = activeTuition?.amount || 0;

  if (loading && !tuitionData) {
    return (
      <div className="tdtu-container">
        <div className="tdtu-skeleton-title" />
        <div className="tdtu-skeleton-table" />
      </div>
    );
  }

  if (loadError && !tuitionData) {
    return (
      <div className="tdtu-container">
        <div className="tdtu-alert tdtu-alert-error">
          {loadError}
          <button className="tdtu-btn-retry" onClick={loadAll}>Thử lại</button>
        </div>
      </div>
    );
  }

  /* RENDER VIEW: THÔNG TIN SINH VIÊN */
  if (topTab === "student_info") {
    return (
      <div className="tdtu-container">
        <div className="tdtu-student-profile-card">
          <div className="tdtu-profile-header">
            <h2>THÔNG TIN SINH VIÊN</h2>
          </div>

          <div className="tdtu-profile-grid">
            <div className="tdtu-profile-field">
              <span className="lbl">Mã số sinh viên (MSSV):</span>
              <span className="val bold">{meData?.username || s?.student_id || "521H0092"}</span>
            </div>

            <div className="tdtu-profile-field">
              <span className="lbl">Họ và tên:</span>
              <span className="val bold">{meData?.full_name || s?.full_name || "Võ Thị Thiên Kim"}</span>
            </div>

            <div className="tdtu-profile-field">
              <span className="lbl">Khoa:</span>
              <span className="val">{s?.faculty?.name || "Công nghệ thông tin"}</span>
            </div>

            <div className="tdtu-profile-field">
              <span className="lbl">Ngành:</span>
              <span className="val">{s?.major?.name || "Kỹ thuật phần mềm"}</span>
            </div>

            <div className="tdtu-profile-field">
              <span className="lbl">Hệ đào tạo:</span>
              <span className="val">{s?.edu_system?.name || "Chính quy"}</span>
            </div>

            <div className="tdtu-profile-field">
              <span className="lbl">Email sinh viên:</span>
              <span className="val">{meData?.email || "521h0092@student.tdtu.edu.vn"}</span>
            </div>

            <div className="tdtu-profile-field">
              <span className="lbl">Số điện thoại:</span>
              <span className="val">{meData?.phone || "0901234567"}</span>
            </div>

            <div className="tdtu-profile-field balance-field">
              <span className="lbl">Số dư tài khoản khả dụng:</span>
              <span className="val highlight">
                {money.format(payerData?.available_balance || 15000000)} ₫
              </span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  /* RENDER VIEW: HỌC PHÍ - CHI PHÍ (DEFAULT) */
  return (
    <div className="tdtu-container">
      {/* FILTER HỌC KỲ */}
      <div className="tdtu-semester-filter">
        <label htmlFor="semester-select" className="tdtu-filter-label">
          Học kỳ | Semester
        </label>

        <div className="tdtu-select-wrapper">
          <select
            id="semester-select"
            className="tdtu-select"
            value={selectedSemester}
            onChange={(e) => setSelectedSemester(e.target.value)}
          >
            <option value="">--Chọn học kỳ | Choose semester--</option>
            <option value="Học kỳ 1/ 2026 - 2027">Học kỳ 1/ 2026 - 2027 | 1st semester/2026 - 2027</option>
            <option value="Học kỳ 3/ 2025 - 2026">Học kỳ 3/ 2025 - 2026 | 3rd semester/2025 - 2026</option>
            <option value="Học kỳ 2/ 2025 - 2026">Học kỳ 2/ 2025 - 2026 | 2nd semester/2025 - 2026</option>
            <option value="Học kỳ 1/ 2025 - 2026">Học kỳ 1/ 2025 - 2026 | 1st semester/2025 - 2026</option>
            <option value="Học kỳ 3/ 2024 - 2025">Học kỳ 3/ 2024 - 2025 | 3rd semester/2024 - 2025</option>
            <option value="Học kỳ 2/ 2024 - 2025">Học kỳ 2/ 2024 - 2025 | 2nd semester/2024 - 2025</option>
            <option value="Học kỳ 1/ 2024 - 2025">Học kỳ 1/ 2024 - 2025 | 1st semester/2024 - 2025</option>
          </select>
        </div>
      </div>

      {/* SUB TABS BAR (STYLED LIKE TOP NAV BAR) */}
      <div className="tdtu-sub-tabs-bar">
        <div className="tdtu-sub-tabs">
          <button
            className={`tdtu-sub-tab ${activeSubTab === "tuition" ? "active" : ""}`}
            onClick={() => setActiveSubTab("tuition")}
          >
            Học phí | Tuition
          </button>
          <button
            className={`tdtu-sub-tab ${activeSubTab === "payment" ? "active" : ""}`}
            onClick={() => setActiveSubTab("payment")}
          >
            Thanh toán | Payment
          </button>
        </div>
      </div>

      {payError && <div className="tdtu-alert tdtu-alert-error">{payError}</div>}

      {/* DYNAMIC SUB TAB CONTENT */}
      {activeSubTab === "tuition" ? (
        /* SUB TAB: HỌC PHÍ | TUITION */
        <div className="tdtu-tab-content fade-in">
          {/* TABLE BẢNG TỔNG HỢP HỌC PHÍ (SUMMARY TABLE) */}
          <div className="tdtu-table-responsive">
            <table className="tdtu-table tdtu-summary-table">
              <thead>
                <tr>
                  <th>
                    NỢ KỲ TRƯỚC<br />
                    <span className="sub-header">(Previous Pending Charges)</span><br />
                    <span className="col-num">(1)</span>
                  </th>
                  <th>
                    HỌC PHÍ HỌC KỲ<br />
                    <span className="sub-header">(Semester Tuition)</span><br />
                    <span className="col-num">(2)</span>
                  </th>
                  <th>
                    MIỄN GIẢM<br />
                    <span className="sub-header">(Reduction)</span><br />
                    <span className="col-num">(3)</span>
                  </th>
                  <th>
                    TỔNG HP PHẢI NỘP<br />
                    <span className="sub-header">(Total Tuition unpaid)</span><br />
                    <span className="col-num">(4) = (1) + (2) - (3)</span>
                  </th>
                  <th>
                    TỔNG HỌC PHÍ ĐÃ NỘP<br />
                    <span className="sub-header">(Total tuition paid)</span><br />
                    <span className="col-num">(5)</span>
                  </th>
                  <th>
                    SỐ TIỀN CÒN PHẢI NỘP<br />
                    <span className="sub-header">(Remaining unpaid tuition)</span><br />
                    <span className="col-num">(6) = (4) - (5)</span>
                  </th>
                  <th>
                    GHI CHÚ<br />
                    <span className="sub-header">(Note)</span><br />
                    <span className="col-num">(7)</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>0</td>
                  <td>{money.format(tuitionAmount)}</td>
                  <td>0</td>
                  <td className={!isPaid && tuitionAmount > 0 ? "text-danger bold" : ""}>
                    {money.format(tuitionAmount)}
                  </td>
                  <td className={isPaid ? "text-success bold" : ""}>
                    {isPaid ? money.format(tuitionAmount) : 0}
                  </td>
                  <td className={!isPaid && tuitionAmount > 0 ? "text-danger bold" : ""}>
                    {!isPaid ? money.format(tuitionAmount) : 0}
                  </td>
                  <td>0</td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* DETAILED SUBJECT TABLE */}
          <div className="tdtu-subject-section">
            <div className="tdtu-table-responsive">
              <table className="tdtu-table tdtu-subject-table">
                <thead>
                  <tr>
                    <th>Mã MH<br /><span className="sub-header">(Course code)</span></th>
                    <th>Tên MH<br /><span className="sub-header">(Course name)</span></th>
                    <th>Nhóm<br /><span className="sub-header">(Group)</span></th>
                    <th>Số tiền<br /><span className="sub-header">(Amount)</span></th>
                    <th>Trạng thái<br /><span className="sub-header">(Status)</span></th>
                  </tr>
                </thead>
                <tbody>
                  {items.length === 0 ? (
                    <tr>
                      <td colSpan="5" className="text-center">Chưa có thông tin môn học nào</td>
                    </tr>
                  ) : (
                    items.map((item, idx) => (
                      <tr key={item.subject_code || idx}>
                        <td className="code-cell">{item.subject_code}</td>
                        <td className="name-cell">{item.subject_name}</td>
                        <td className="group-cell">{11 + (idx % 3)}</td>
                        <td className="bold col-money-nowrap">{money.format(item.amount || 2250000)} ₫</td>
                        <td>
                          {isPaid ? (
                            <span className="text-success bold">Đã nộp</span>
                          ) : (
                            <span className="text-danger bold">Chưa nộp</span>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            <div className="tdtu-subject-total">
              <strong>Tổng cộng | Total: {items.length} môn</strong>
            </div>
          </div>

          {/* PAYMENT HISTORY SECTION (LOCATED INSIDE HỌC PHÍ TAB) */}
          <div className="tdtu-history-section">
            <h3 className="tdtu-history-title">Lịch sử thanh toán | Payment history</h3>
            <div className="tdtu-table-responsive">
              <table className="tdtu-table tdtu-history-table">
                <thead>
                  <tr>
                    <th>Ngày đóng<br /><span className="sub-header">(Date of payment)</span></th>
                    <th>Số tiền<br /><span className="sub-header">(Amount)</span></th>
                    <th>Hình thức thanh toán<br /><span className="sub-header">(Method of payment)</span></th>
                  </tr>
                </thead>
                <tbody>
                  {paymentHistory.length === 0 ? (
                    <tr>
                      <td colSpan="3" className="text-center">Chưa có lịch sử thanh toán nào</td>
                    </tr>
                  ) : (
                    paymentHistory.map((h, i) => (
                      <tr key={h.payment_id || i}>
                        <td>{fmtDate(h.completed_at || h.created_at)}</td>
                        <td className="bold col-money-nowrap">{money.format(h.amount)} ₫</td>
                        <td>CK</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
            <div className="tdtu-history-footer-note">
              Hình thức thanh toán: TM: Tiền mặt. CK: Chuyển khoản | Method of payment: TM - Cash; CK: Transfer
            </div>
          </div>
        </div>
      ) : (
        /* SUB TAB: THANH TOÁN | PAYMENT (MATCHING ATTACHED SCREENSHOT) */
        <div className="tdtu-tab-content fade-in">
          <div className="tdtu-table-responsive">
            <table className="tdtu-table tdtu-payment-list-table">
              <thead>
                <tr>
                  <th>STT<br /><span className="sub-header">(Index)</span></th>
                  <th>Dịch vụ<br /><span className="sub-header">(Service)</span></th>
                  <th>Ghi chú<br /><span className="sub-header">(Note)</span></th>
                  <th>Thời gian đóng<br /><span className="sub-header">(Payment deadline)</span></th>
                  <th>Số tiền<br /><span className="sub-header">(Amount)</span></th>
                  <th>Trạng thái thanh toán<br /><span className="sub-header">(Status)</span></th>
                  <th style={{ textAlign: "center" }}>Thanh toán</th>
                </tr>
              </thead>
              <tbody>
                {!activeTuition ? (
                  <tr>
                    <td colSpan="7" className="text-center">Chưa có dữ liệu học phí</td>
                  </tr>
                ) : (
                  <tr>
                    <td>1</td>
                    <td>Học phí</td>
                    <td className="name-cell">
                      Thông báo nộp học phí {activeTuition.semester}/2026-2027 dành cho sinh viên trình độ Đại học (TB số 26/2026/PTC-TB)
                    </td>
                    <td className="col-money-nowrap">09/06/2026 -&gt; 20/06/2026</td>
                    <td className="text-danger bold col-money-nowrap">{money.format(activeTuition.amount)} ₫</td>
                    <td>
                      {isPaid ? (
                        <span className="text-success bold">Đã thanh toán</span>
                      ) : (
                        <span className="text-danger bold">Chưa thanh toán</span>
                      )}
                    </td>
                    <td style={{ textAlign: "center" }}>
                      {!isPaid && (
                        <button
                          className="tdtu-btn-pay tdtu-btn-pay-fit"
                          disabled={paying !== null}
                          onClick={() => handlePay(activeTuition)}
                        >
                          {paying === activeTuition.tuition_id ? "Đang xử lý…" : "Thanh toán"}
                        </button>
                      )}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* FLOATING MASCOT BOT WIDGET */}
      <div className="tdtu-bot-widget" title="Hỗ trợ sinh viên">
        <div className="tdtu-bot-circle">
          <svg viewBox="0 0 24 24" width="28" height="28" fill="white">
            <path d="M12 2a2 2 0 0 1 2 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 0 1 7 7h1a1 1 0 0 1 1 1v3a1 1 0 0 1-1 1h-1v1a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-1H2a1 1 0 0 1-1-1v-3a1 1 0 0 1 1-1h1a7 7 0 0 1 7-7h1V5.73c-.6-.34-1-.99-1-1.73a2 2 0 0 1 2-2zM7.5 13a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zm9 0a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3z" />
          </svg>
        </div>
      </div>
    </div>
  );
}

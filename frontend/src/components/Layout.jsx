import { useState, useEffect, useCallback } from "react";
import { Outlet, useNavigate, useLocation } from "react-router-dom";
import { ApiClient, API_ENDPOINTS } from "../api/client.js";

export default function Layout() {
  const navigate = useNavigate();
  const location = useLocation();
  const [me, setMe] = useState(null);
  const [payer, setPayer] = useState(null);
  const [tuition, setTuition] = useState(null);
  const [topTab, setTopTab] = useState("tuition"); // 'tuition' | 'student_info'

  const loadData = useCallback(async () => {
    try {
      const [meRes, payerRes, tuitionRes] = await Promise.allSettled([
        ApiClient.get(API_ENDPOINTS.auth.me),
        ApiClient.get(API_ENDPOINTS.payers.me),
        ApiClient.get(API_ENDPOINTS.tuition.me),
      ]);

      if (meRes.status === "fulfilled") setMe(meRes.value);
      if (payerRes.status === "fulfilled") setPayer(payerRes.value);
      if (tuitionRes.status === "fulfilled") setTuition(tuitionRes.value);
    } catch (err) {
      console.error("Error loading layout data:", err);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  async function handleLogout() {
    try {
      await ApiClient.post(API_ENDPOINTS.auth.logout);
    } catch {}
    ApiClient.clearToken();
    navigate("/login", { replace: true });
  }

  const s = tuition?.student || {};

  return (
    <div className="tdtu-layout">
      {/* HEADER BAR - FULL WIDTH */}
      <header className="tdtu-header-full">
        <div className="tdtu-header-inner-full">
          <div
            className="tdtu-brand"
            onClick={() => {
              setTopTab("tuition");
              navigate("/");
            }}
          >
            <img src="/logo.png" alt="TDTU Logo" className="tdtu-header-logo" />
            <h1 className="tdtu-header-title">THÔNG TIN HỌC PHÍ - LỆ PHÍ</h1>
          </div>

          <div className="tdtu-user-section">
            <span className="tdtu-student-name">
              {me?.full_name || s?.full_name || "Võ Thị Thiên Kim"}
            </span>

            {/* HOME ICON BUTTON */}
            <button
              className="tdtu-icon-btn tdtu-home-btn"
              onClick={() => {
                setTopTab("tuition");
                navigate("/");
              }}
              title="Trang chủ"
            >
              <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
                <path d="M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z" />
              </svg>
            </button>

            {/* LOGOUT ICON BUTTON */}
            <button
              className="tdtu-icon-btn tdtu-logout-btn"
              onClick={handleLogout}
              title="Đăng xuất"
            >
              <svg
                viewBox="0 0 24 24"
                width="20"
                height="20"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M18.36 6.64a9 9 0 1 1-12.73 0" />
                <line x1="12" y1="2" x2="12" y2="12" />
              </svg>
            </button>
          </div>
        </div>
      </header>

      {/* SUB BAR NAVIGATION - ALIGNED WITH CONTENT */}
      <div className="tdtu-subbar">
        <div className="tdtu-subbar-container">
          <div className="tdtu-tabs">
            <button
              className={`tdtu-tab ${topTab === "tuition" && location.pathname === "/" ? "active" : ""}`}
              onClick={() => {
                setTopTab("tuition");
                if (location.pathname !== "/") navigate("/");
              }}
            >
              Học phí - Chi phí | Tuition - Charges
            </button>

            <button
              className={`tdtu-tab ${topTab === "student_info" ? "active" : ""}`}
              onClick={() => {
                setTopTab("student_info");
                if (location.pathname !== "/") navigate("/");
              }}
            >
              Thông tin sinh viên
            </button>
          </div>
        </div>
      </div>

      {/* MAIN CONTENT AREA */}
      <main className="tdtu-main-content">
        <Outlet context={{ me, payer, tuition, loadData, topTab, setTopTab }} />
      </main>
    </div>
  );
}

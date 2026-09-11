import { useState, useEffect } from "react";
import { Outlet, NavLink, useNavigate } from "react-router-dom";
import { ApiClient, API_ENDPOINTS } from "../api/client.js";

export default function Layout() {
  const navigate = useNavigate();
  const [me, setMe] = useState(null);

  useEffect(() => {
    ApiClient.get(API_ENDPOINTS.auth.me).then(setMe).catch(() => {});
  }, []);

  async function handleLogout() {
    try {
      await ApiClient.post(API_ENDPOINTS.auth.logout);
    } catch {
    }
    ApiClient.clearToken();
    navigate("/login", { replace: true });
  }

  const initial = (me?.full_name || "?").trim().charAt(0).toUpperCase();

  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">iB</span>
          <span className="brand-name">iBanking <small>Thanh toán học phí TDTU</small></span>
        </div>
        <nav className="topnav">
          <NavLink to="/" end>Học phí</NavLink>
          <NavLink to="/history">Lịch sử giao dịch</NavLink>
        </nav>
        <div className="topbar-user">
          {me && (
            <span className="user-chip" title={me.username}>
              <span className="avatar">{initial}</span>
              <span className="user-name">{me.full_name}</span>
            </span>
          )}
          <button className="btn btn-ghost" onClick={handleLogout}>Đăng xuất</button>
        </div>
      </header>
      <main className="content">
        <Outlet />
      </main>
      <footer className="footer">Hệ thống thanh toán học phí — Kiến trúc hướng dịch vụ (SOA)</footer>
    </div>
  );
}

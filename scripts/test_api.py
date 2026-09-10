"""Bộ test khói (smoke test) cho 3 service nền tảng.

Yêu cầu: đã chạy auth(:8001), payer(:8002), tuition(:8003) — xem scripts/run_dev.bat.

Chạy từ thư mục gốc:
    python scripts/test_api.py

Mỗi test in PASS/FAIL; tổng kết ở cuối; exit code != 0 nếu có test lỗi.
"""
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "services"))
from shared import config  # noqa: E402

AUTH = "http://localhost:8001"
PAYER = "http://localhost:8002"
TUITION = "http://localhost:8003"
INTERNAL = {"X-Internal-Token": config.INTERNAL_TOKEN}

USER_OK = "521H0092"   # uid 1 — số dư 15.000.000, học phí 7.000.000
PW_OK = "abc12345"

_results = []


def check(name: str, cond: bool, note: str = ""):
    _results.append(cond)
    mark = "✅ PASS" if cond else "❌ FAIL"
    print(f"{mark}  {name}" + (f"  — {note}" if note else ""))


def api_error(resp: httpx.Response) -> str:
    try:
        err = resp.json().get("error", {})
        return f"{resp.status_code} {err.get('code')}: {err.get('message')}"
    except Exception:
        return f"{resp.status_code} {resp.text[:120]}"


def _token_of(username: str) -> str:
    """Lấy token của 1 tài khoản demo khác (dùng để test quyền truy cập chéo)."""
    r = httpx.post(f"{AUTH}/auth/login", json={"username": username, "password": PW_OK})
    return r.json().get("token", "") if r.status_code == 200 else ""


def main():
    print("=" * 64)
    print("TEST API — iBanking Tuition Payment (auth + payer + tuition)")
    print("=" * 64)

    # ---------- T01: health ----------
    try:
        for name, base in [("auth", AUTH), ("payer", PAYER), ("tuition", TUITION)]:
            r = httpx.get(f"{base}/health", timeout=5)
            check(f"T01 /health {name}", r.status_code == 200 and r.json().get("status") == "ok", api_error(r))
    except httpx.ConnectError:
        print("❌ FAIL  Không kết nối được service — đã chạy scripts/run_dev.bat chưa?")
        print("=" * 64)
        sys.exit(1)

    # ---------- T02-T04: login ----------
    r = httpx.post(f"{AUTH}/auth/login", json={"username": USER_OK, "password": PW_OK})
    check("T02 login đúng mật khẩu -> 200 + token", r.status_code == 200 and "token" in r.json(), api_error(r))
    token = r.json().get("token", "") if r.status_code == 200 else ""
    headers = {"Authorization": f"Bearer {token}"}

    r = httpx.post(f"{AUTH}/auth/login", json={"username": USER_OK, "password": "sai-mat-khau"})
    check("T03 login sai mật khẩu -> 401 AUTH_INVALID_CREDENTIALS",
          r.status_code == 401 and r.json()["error"]["code"] == "AUTH_INVALID_CREDENTIALS", api_error(r))

    r = httpx.post(f"{AUTH}/auth/login", json={"username": "521H009", "password": PW_OK})  # thiếu 1 ký tự
    check("T04 login MSSV sai định dạng -> 400 VALIDATION_ERROR",
          r.status_code == 400 and r.json()["error"]["code"] == "VALIDATION_ERROR", api_error(r))

    # ---------- T05-T06: /auth/me ----------
    r = httpx.get(f"{AUTH}/auth/me")
    check("T05 /auth/me không kèm token -> 401", r.status_code == 401, api_error(r))

    r = httpx.get(f"{AUTH}/auth/me", headers=headers)
    ok = r.status_code == 200 and r.json().get("uid") == 1 and r.json().get("username") == USER_OK
    check("T06 /auth/me có token -> 200, uid=1", bool(ok) and token != "", api_error(r))

    # ---------- T07: /payers/me ----------
    r = httpx.get(f"{PAYER}/payers/me", headers=headers)
    ok = r.status_code == 200 and r.json().get("available_balance") == 15000000
    check("T07 /payers/me -> 200, số dư 15.000.000", r.status_code == 200 and ok, api_error(r))

    # ---------- T08: /tuition/me ----------
    r = httpx.get(f"{TUITION}/tuition/me", headers=headers)
    if r.status_code == 200:
        data = r.json()
        st, tui = data.get("student", {}), data.get("tuitions", [])
        hk1 = next((t for t in tui if t["semester"] == "2025-2026-HK1"), None)
        check("T08a /tuition/me -> 200, đúng MSSV + trường TDTU",
              st.get("student_id") == USER_OK and "Tôn Đức Thắng" in st.get("school", {}).get("name", ""),
              f"student_id={st.get('student_id')}, school={st.get('school', {}).get('name')}")
        check("T08b có khoản 2025-2026-HK1: 7.000.000 UNPAID",
              hk1 is not None and hk1["amount"] == 7000000 and hk1["status"] == "UNPAID",
              f"{hk1}" if hk1 else "không tìm thấy HK1")
        check("T08c hồ sơ có đủ trường/khoa/ngành/hệ + mã hệ",
              bool(st.get("school") and st.get("faculty") and st.get("major")
                   and st.get("edu_system", {}).get("code")),
              f"faculty={st.get('faculty')}, major={st.get('major')}, hệ={st.get('edu_system')}")
    else:
        check("T08 /tuition/me -> 200", False, api_error(r))

    # ---------- T09-T12: trừ/hoàn tiền nội bộ (uid 2 — balance 2.000.000) ----------
    pid = 9000000 + (int(time.time() * 1000) % 1000000)  # unique mỗi lần chạy
    amt = 1500000
    r = httpx.post(f"{PAYER}/internal/balance/capture", headers=INTERNAL,
                   json={"payment_id": pid, "uid": 2, "amount": amt})
    ok = r.status_code == 200 and r.json().get("captured") and r.json().get("balance_after") == 500000
    check("T09 internal capture uid2 (1.5M) -> balance còn 500.000", ok, api_error(r))

    r = httpx.post(f"{PAYER}/internal/balance/capture", headers=INTERNAL,
                   json={"payment_id": pid, "uid": 2, "amount": amt})
    ok = r.status_code == 200 and r.json().get("idempotent") and r.json().get("balance_after") == 500000
    check("T10 capture lại cùng payment_id -> idempotent, KHÔNG trừ thêm", ok, api_error(r))

    r = httpx.post(f"{PAYER}/internal/balance/release", headers=INTERNAL,
                   json={"payment_id": pid, "uid": 2, "amount": amt})
    ok = r.status_code == 200 and r.json().get("released") and r.json().get("balance_after") == 2000000
    check("T11 internal release -> balance về 2.000.000", ok, api_error(r))

    r = httpx.post(f"{PAYER}/internal/balance/release", headers=INTERNAL,
                   json={"payment_id": pid, "uid": 2, "amount": amt})
    ok = r.status_code == 200 and r.json().get("idempotent") and r.json().get("balance_after") == 2000000
    check("T12 release lại -> idempotent, KHÔNG cộng thêm", ok, api_error(r))

    # ---------- T13-T14: thiếu dư + bảo mật nội bộ ----------
    r = httpx.post(f"{PAYER}/internal/balance/capture", headers=INTERNAL,
                   json={"payment_id": pid + 1, "uid": 3, "amount": 5000000})
    ok = r.status_code == 422 and r.json()["error"]["code"] == "INSUFFICIENT_BALANCE"
    check("T13 uid3 (1.000.000) capture 5M -> 422 INSUFFICIENT_BALANCE", ok, api_error(r))

    r = httpx.post(f"{PAYER}/internal/balance/capture",
                   json={"payment_id": pid + 2, "uid": 2, "amount": 1000})
    check("T14 internal KHÔNG kèm X-Internal-Token -> 403", r.status_code == 403, api_error(r))

    # ---------- T15-T18: khóa/mở tuition ----------
    r_tui = httpx.get(f"{TUITION}/tuition/me", headers=headers)
    tui_list = r_tui.json().get("tuitions", []) if r_tui.status_code == 200 else []
    hk1 = next((t for t in tui_list if t["semester"] == "2025-2026-HK1"), None)
    tuition_id = hk1["tuition_id"] if hk1 else None

    # ---------- T19-T22: môn đã đăng ký + người nhận (trang thanh toán) ----------
    if tuition_id:
        r = httpx.get(f"{TUITION}/tuitions/{tuition_id}/enrollments", headers=headers)
        if r.status_code == 200:
            d = r.json()
            enr = d.get("enrollments", [])
            check("T19 /tuitions/{id}/enrollments -> 5 môn đã đăng ký của HK1",
                  len(enr) == 5, f"số môn = {len(enr)}")
            check("T20 tổng học phí các môn = 7.000.000 = số tiền học kỳ",
                  d.get("total_amount") == 7000000 and d.get("amount_matches_enrollments") is True,
                  f"total_amount={d.get('total_amount')}, khớp={d.get('amount_matches_enrollments')}")
            check("T21 mỗi môn có mã môn + tên môn + tín chỉ + số tiền",
                  all(e.get("subject_id") and e.get("subject_name") and e.get("credits") and e.get("amount")
                      for e in enr) and d.get("total_credits") == 14,
                  f"tổng tín chỉ = {d.get('total_credits')}")
            check("T22 có thông tin người nhận (tên + ngân hàng + số tài khoản)",
                  bool(d.get("beneficiary", {}).get("name") and d["beneficiary"].get("bank_name")
                       and d["beneficiary"].get("account_no")),
                  f"{d.get('beneficiary')}")
        else:
            check("T19-T22 /tuitions/{id}/enrollments -> 200", False, api_error(r))

        r = httpx.get(f"{TUITION}/tuitions/{tuition_id}/enrollments",
                      headers={"Authorization": f"Bearer {_token_of('522H0145')}"})
        check("T23 xem môn đã đăng ký của học kỳ người khác -> 403", r.status_code == 403, api_error(r))

    if tuition_id:
        r = httpx.post(f"{TUITION}/internal/tuitions/{tuition_id}/lock", headers=INTERNAL,
                       json={"uid": 1, "payment_id": pid + 10})
        check("T15 internal lock tuition -> PAYING", r.status_code == 200 and r.json().get("status") == "PAYING", api_error(r))

        r = httpx.get(f"{TUITION}/internal/tuitions/{tuition_id}", headers=INTERNAL, params={"uid": 1})
        check("T16 internal get tuition -> 200 PAYING",
              r.status_code == 200 and r.json().get("status") == "PAYING", api_error(r))

        r = httpx.post(f"{TUITION}/internal/tuitions/{tuition_id}/release", headers=INTERNAL,
                       json={"uid": 1, "payment_id": pid + 10})
        check("T17 internal release tuition -> UNPAID", r.status_code == 200 and r.json().get("status") == "UNPAID", api_error(r))

        r = httpx.post(f"{TUITION}/internal/tuitions/{tuition_id}/lock", headers=INTERNAL,
                       json={"uid": 2, "payment_id": pid + 11})  # uid2 khác chủ (uid1)
        check("T18 người khác lock tuition của uid1 -> 403", r.status_code == 403, api_error(r))
    else:
        check("T15-T18 cần tuition_id từ /tuition/me", False, "không lấy được tuition_id")

    # ---------- T24: an toàn tiền — hoàn tiền khi CHƯA từng trừ thì không được cộng ----------
    fresh_pid = pid + 500
    r = httpx.post(f"{PAYER}/internal/balance/release", headers=INTERNAL,
                   json={"payment_id": fresh_pid, "uid": 2, "amount": 1000000})
    ok = (r.status_code == 200 and r.json().get("released") is False
          and r.json().get("reason") == "NOT_CAPTURED" and r.json().get("balance_after") == 2000000)
    check("T24 release payment chưa capture -> KHÔNG cộng tiền (skipped NOT_CAPTURED)", ok, api_error(r))

    # ---------- Tổng kết ----------
    print("=" * 64)
    passed, failed = sum(_results), len(_results) - sum(_results)
    print(f"KẾT QUẢ: {passed}/{len(_results)} PASS, {failed} FAIL")
    print("=" * 64)
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
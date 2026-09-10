"""Bộ test riêng cho otp-service (:8005) — FR-04, FR-05, BR-08, BR-09.

Khác với test_api.py: dùng payment_id "ảo" (timestamp) + uid test riêng để không
đụng dữ liệu giao dịch thật; tự dọn bản ghi test sau khi chạy.

Yêu cầu: otp-service đang chạy ở :8005.
    python -m uvicorn main:app --port 8005 --app-dir services/otp-service

Chạy từ thư mục gốc:
    python scripts/test_otp.py
"""
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "services"))
from shared import config  # noqa: E402
from shared.db import connect  # noqa: E402

OTP = "http://localhost:8005"
INTERNAL = {"X-Internal-Token": config.INTERNAL_TOKEN}
UID_TEST = 999999   # uid không tồn tại trong AuthDB — chỉ để kiểm tra vòng đời OTP

_results = []


def check(name: str, cond: bool, note: str = ""):
    _results.append(cond)
    mark = "✅ PASS" if cond else "❌ FAIL"
    print(f"{mark}  {name}" + (f"  — {note}" if note else ""))


def api_error(resp: httpx.Response) -> str:
    try:
        err = resp.json().get("error", {})
        return f"{resp.status_code} {err.get('code')}: {err.get('message')} ({err.get('detail')})"
    except Exception:
        return f"{resp.status_code} {resp.text[:120]}"


def db_status(payment_id: int):
    """Đọc trực tiếp OTPDB để đối chiếu trạng thái thật trong DB."""
    with connect("OTPDB") as c:
        return c.execute(
            "SELECT otp_id, code, status, attempts, used_at, invalidated_at, status_reason "
            "FROM dbo.otps WHERE payment_id = ? ORDER BY otp_id DESC",
            payment_id,
        ).fetchall()


def main():
    print("=" * 64)
    print("TEST OTP SERVICE — iBanking Tuition Payment (otp-service :8005)")
    print("=" * 64)

    try:
        r = httpx.get(f"{OTP}/health", timeout=5)
        assert r.status_code == 200
    except Exception:
        print("❌ FAIL  Không kết nối được otp-service :8005 — đã khởi động chưa?")
        sys.exit(1)
    check("O01 /health", r.json().get("status") == "ok")

    pid_base = int(time.time()) * 10   # payment_id ảo, mỗi lần chạy khác nhau

    # Dọn bản ghi test sót từ lần chạy trước bị ngắt giữa chừng (uid test + pid ảo cũ)
    with connect("OTPDB") as c:
        c.execute("DELETE FROM dbo.otps WHERE uid = ?", UID_TEST)
    check("O01b dọn dữ liệu test cũ", True)

    # ---------- generate ----------
    pid1 = pid_base + 1
    r = httpx.post(f"{OTP}/internal/otp/generate", timeout=10,
                   headers=INTERNAL,
                   json={"uid": UID_TEST, "payment_id": pid1,
                         "email": "test@example.com", "purpose": "TUITION_PAYMENT"})
    ok = r.status_code == 200 and len(r.json().get("code", "")) == 6
    check("O02 generate -> 200, mã 6 số, hạn 300s", ok and r.json().get("code", "").isdigit(),
          api_error(r) if not ok else r.json().get("code"))
    code1 = r.json().get("code", "000000")

    rows = db_status(pid1)
    check("O03 DB: bản ghi ACTIVE, attempts=0",
          len(rows) == 1 and rows[0].status == "ACTIVE" and rows[0].attempts == 0)

    r = httpx.post(f"{OTP}/internal/otp/generate", timeout=10, headers=INTERNAL,
                   json={"uid": UID_TEST, "payment_id": pid1, "email": "test@example.com"})
    code2 = r.json().get("code", "")
    check("O04 generate lần 2 -> mã MỚI khác mã cũ", r.status_code == 200 and code2 != code1)
    rows = db_status(pid1)
    check("O05 DB: mã cũ -> REPLACED, mã mới ACTIVE",
          len(rows) == 2 and rows[1].status == "REPLACED" and rows[0].status == "ACTIVE")

    # ---------- verify đúng/sai ----------
    r = httpx.post(f"{OTP}/internal/otp/verify", timeout=10, headers=INTERNAL,
                   json={"payment_id": pid1, "code": "000001"})   # cố tình sai
    ok = r.status_code == 400 and r.json()["error"]["code"] == "OTP_INVALID"
    check("O06 verify sai 1 lần -> 400 OTP_INVALID (kèm số lần còn lại)",
          ok and "Còn" in r.json()["error"].get("detail", ""), api_error(r))
    rows = db_status(pid1)
    check("O07 DB: attempts=1, vẫn ACTIVE", rows[0].attempts == 1 and rows[0].status == "ACTIVE")

    r = httpx.post(f"{OTP}/internal/otp/verify", timeout=10, headers=INTERNAL,
                   json={"payment_id": pid1, "code": code2})
    check("O08 verify đúng -> 200 verified", r.status_code == 200 and r.json().get("verified"),
          api_error(r))
    rows = db_status(pid1)
    check("O09 DB: status USED, có used_at (BR-08 dùng 1 lần)",
          rows[0].status == "USED" and rows[0].used_at is not None)

    r = httpx.post(f"{OTP}/internal/otp/verify", timeout=10, headers=INTERNAL,
                   json={"payment_id": pid1, "code": code2})
    ok = r.status_code == 400 and r.json()["error"]["code"] == "OTP_USED"
    check("O10 verify lại mã đã dùng -> 400 OTP_USED", ok, api_error(r))

    # ---------- sai đủ 5 lần -> LOCKED ----------
    pid2 = pid_base + 2
    httpx.post(f"{OTP}/internal/otp/generate", timeout=10, headers=INTERNAL,
               json={"uid": UID_TEST, "payment_id": pid2, "email": "test@example.com"})
    codes = []
    for i in range(4):   # sai 4 lần đầu vẫn ACTIVE
        rr = httpx.post(f"{OTP}/internal/otp/verify", timeout=10, headers=INTERNAL,
                        json={"payment_id": pid2, "code": f"00000{i + 1}"})
        codes.append(rr.json()["error"]["code"] if rr.status_code == 400 else "OK?")
    rows = db_status(pid2)
    check("O11 sai 4 lần -> đều OTP_INVALID, vẫn ACTIVE",
          all(c == "OTP_INVALID" for c in codes) and rows[0].status == "ACTIVE"
          and rows[0].attempts == 4)

    r = httpx.post(f"{OTP}/internal/otp/verify", timeout=10, headers=INTERNAL,
                   json={"payment_id": pid2, "code": "999999"})
    ok = r.status_code == 400 and r.json()["error"]["code"] == "OTP_LOCKED"
    check("O12 sai lần 5 -> 400 OTP_LOCKED (BR-09)", ok, api_error(r))
    rows = db_status(pid2)
    check("O13 DB: status LOCKED, attempts=5", rows[0].status == "LOCKED" and rows[0].attempts == 5)

    r = httpx.post(f"{OTP}/internal/otp/verify", timeout=10, headers=INTERNAL,
                   json={"payment_id": pid2, "code": "123456"})
    check("O14 verify khi đã LOCKED -> vẫn OTP_LOCKED",
          r.status_code == 400 and r.json()["error"]["code"] == "OTP_LOCKED", api_error(r))

    # ---------- hết hạn -> EXPIRED ----------
    pid3 = pid_base + 3
    r = httpx.post(f"{OTP}/internal/otp/generate", timeout=10, headers=INTERNAL,
                   json={"uid": UID_TEST, "payment_id": pid3, "email": "test@example.com"})
    code3 = r.json().get("code", "")
    # Ép hết hạn: lùi cả created_at + expires_at về quá khứ (CHECK expires_at > created_at)
    with connect("OTPDB") as c:
        c.execute(
            "UPDATE dbo.otps SET created_at = DATEADD(SECOND, -3600, SYSUTCDATETIME()), "
            "expires_at = DATEADD(SECOND, -60, SYSUTCDATETIME()) "
            "WHERE payment_id = ? AND status = N'ACTIVE'", pid3)
    r = httpx.post(f"{OTP}/internal/otp/verify", timeout=10, headers=INTERNAL,
                   json={"payment_id": pid3, "code": code3})
    ok = r.status_code == 400 and r.json()["error"]["code"] == "OTP_EXPIRED"
    check("O15 verify mã hết hạn -> 400 OTP_EXPIRED", ok, api_error(r))
    rows = db_status(pid3)
    check("O16 DB: status EXPIRED", rows[0].status == "EXPIRED")

    # ---------- invalidate ----------
    pid4 = pid_base + 4
    httpx.post(f"{OTP}/internal/otp/generate", timeout=10, headers=INTERNAL,
               json={"uid": UID_TEST, "payment_id": pid4, "email": "test@example.com"})
    r = httpx.post(f"{OTP}/internal/otp/invalidate", timeout=10, headers=INTERNAL,
                   json={"payment_id": pid4})
    check("O17 invalidate -> 200, status CANCELLED",
          r.status_code == 200 and r.json().get("status") == "CANCELLED", api_error(r))
    r = httpx.post(f"{OTP}/internal/otp/invalidate", timeout=10, headers=INTERNAL,
                   json={"payment_id": pid4})
    check("O18 invalidate lần 2 -> vẫn 200 (idempotent)",
          r.status_code == 200 and r.json().get("updated") is False, api_error(r))
    rows = db_status(pid4)
    check("O19 DB: status CANCELLED, có invalidated_at, bản ghi KHÔNG bị xóa",
          rows[0].status == "CANCELLED" and rows[0].invalidated_at is not None)

    r = httpx.post(f"{OTP}/internal/otp/verify", timeout=10, headers=INTERNAL,
                   json={"payment_id": pid4, "code": "123456"})
    check("O20 verify sau invalidate -> 400 OTP_INVALID",
          r.status_code == 400 and r.json()["error"]["code"] == "OTP_INVALID", api_error(r))

    # ---------- bảo mật ----------
    r = httpx.post(f"{OTP}/internal/otp/generate", timeout=10,
                   json={"uid": UID_TEST, "payment_id": pid_base + 5, "email": "t@t.com"})
    check("O21 generate thiếu X-Internal-Token -> 403 FORBIDDEN",
          r.status_code == 403 and r.json()["error"]["code"] == "FORBIDDEN", api_error(r))

    r = httpx.post(f"{OTP}/internal/otp/verify", timeout=10, headers=INTERNAL,
                   json={"payment_id": 0, "code": "123456"})
    check("O22 verify payment_id không hợp lệ -> 422/400 validation",
          r.status_code in (400, 422), api_error(r))

    r = httpx.post(f"{OTP}/internal/otp/verify", timeout=10, headers=INTERNAL,
                   json={"payment_id": 999999999, "code": "123456"})
    check("O23 verify payment chưa từng có OTP -> 400 OTP_INVALID",
          r.status_code == 400 and r.json()["error"]["code"] == "OTP_INVALID", api_error(r))

    # ---------- dọn dẹp ----------
    with connect("OTPDB") as c:
        c.execute("DELETE FROM dbo.otps WHERE payment_id >= ? AND payment_id <= ?",
                  pid_base, pid_base + 9)
    check("O24 dọn bản ghi test (xóa đúng vòng đời test, không xóa dữ liệu thật)", True)

    print("=" * 64)
    passed = sum(_results)
    total = len(_results)
    print(f"KẾT QUẢ: {passed}/{total} PASS, {total - passed} FAIL")
    print("=" * 64)
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()

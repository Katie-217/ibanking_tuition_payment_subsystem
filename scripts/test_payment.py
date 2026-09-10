"""Bộ test riêng cho payment-service (:8004) — FR-03 + FR-04 (luồng thanh toán đầy đủ).

Khác với test_api.py: test TOÀN BỘ chuỗi saga qua api-gateway :8000 bằng tài khoản
seed thật (521H0092 / 522H0145 / 523H0201, password abc12345), đối chiếu trạng thái
từng DB. Cuối test TỰ RESET dữ liệu seed (xóa payments/otps/outbox/ledger phát sinh,
trả tuition + balance về giá trị gốc trong 03-seed.sql).

Yêu cầu: đủ 7 service đang chạy (gateway :8000 → auth/payer/tuition/payment/otp/notification).

Chạy từ thư mục gốc:
    PYTHONIOENCODING=utf-8 python scripts/test_payment.py
"""
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "services"))
from shared.db import connect  # noqa: E402

GW = "http://localhost:8000"
SEED_BALANCE = {1: 15_000_000, 2: 2_000_000, 3: 1_000_000}
STUDENTS = {"521H0092": 1, "522H0145": 2, "523H0201": 3}   # username -> uid

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


def login(username: str) -> str:
    r = httpx.post(f"{GW}/auth/login", timeout=10,
                   json={"username": username, "password": "abc12345"})
    assert r.status_code == 200, api_error(r)
    return r.json()["token"]


def first_unpaid_tuition(token: str):
    r = httpx.get(f"{GW}/tuition/me", timeout=10,
                  headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, api_error(r)
    return next(t for t in r.json()["tuitions"] if t["status"] == "UNPAID")


def active_otp_code(payment_id: int) -> str:
    with connect("OTPDB") as c:
        row = c.execute(
            "SELECT code FROM dbo.otps WHERE payment_id = ? AND status = N'ACTIVE'",
            payment_id,
        ).fetchone()
    assert row is not None, f"không tìm thấy OTP ACTIVE cho payment {payment_id}"
    return row.code


def payment_row(payment_id: int):
    with connect("PaymentDB") as c:
        return c.execute(
            "SELECT status, failure_reason, completed_at FROM dbo.payments WHERE payment_id = ?",
            payment_id,
        ).fetchone()


def tuition_status(tuition_id: int) -> str:
    with connect("TuitionDB") as c:
        return c.execute(
            "SELECT status FROM dbo.tuitions WHERE tuition_id = ?", tuition_id,
        ).fetchone().status


def balance(uid: int) -> int:
    with connect("PayerDB") as c:
        return int(c.execute(
            "SELECT available_balance FROM dbo.accounts WHERE payer_uid = ?", uid,
        ).fetchone().available_balance)


def outbox_count(payment_id: int) -> int:
    with connect("NotificationDB") as c:
        return c.execute(
            "SELECT COUNT(*) FROM dbo.email_outbox WHERE payment_id = ?", payment_id,
        ).fetchone()[0]


def reset_seed():
    """Trả toàn bộ dữ liệu giao dịch về đúng 03-seed.sql — chạy ở ĐẦU và CUỐI bộ test."""
    with connect("PaymentDB") as c:
        c.execute("DELETE FROM dbo.payment_history")
        c.execute("DELETE FROM dbo.payments")
    with connect("OTPDB") as c:
        c.execute("DELETE FROM dbo.otps")
    with connect("NotificationDB") as c:
        c.execute("DELETE FROM dbo.email_outbox")
    with connect("PayerDB") as c:
        c.execute("DELETE FROM dbo.balance_ledger")
        for uid, amount in SEED_BALANCE.items():
            c.execute("UPDATE dbo.accounts SET available_balance = ? WHERE payer_uid = ?",
                      amount, uid)
    with connect("TuitionDB") as c:
        c.execute("UPDATE dbo.tuitions SET status = N'UNPAID', paid_at = NULL, "
                  "paid_by_payment_id = NULL WHERE semester = N'2025-2026-HK1'")
        c.execute("UPDATE dbo.tuitions SET status = N'PAID', paid_by_payment_id = NULL "
                  "WHERE semester = N'2024-2025-HK2'")


def main():
    print("=" * 64)
    print("TEST PAYMENT SERVICE — iBanking Tuition Payment (gateway :8000)")
    print("=" * 64)

    try:
        r = httpx.get(f"{GW}/health", timeout=10)
        assert r.status_code == 200 and r.json()["status"] == "ok"
    except Exception:
        print("❌ FAIL  Không kết nối được api-gateway :8000 (hoặc 1 service nào đó down)")
        sys.exit(1)
    check("P01 /health gateway + 7 service", r.json()["status"] == "ok")

    reset_seed()
    check("P02 reset dữ liệu về seed trước khi test", True)

    tok1 = login("521H0092")
    tok2 = login("522H0145")
    tok3 = login("523H0201")

    # ---------- P1x: happy path đầy đủ (uid1, đủ dư) ----------
    tuition = first_unpaid_tuition(tok1)
    tid1, amount1 = tuition["tuition_id"], tuition["amount"]
    headers1 = {"Authorization": f"Bearer {tok1}"}

    r = httpx.post(f"{GW}/payments", timeout=30, headers=headers1, json={"tuition_id": tid1})
    ok = r.status_code == 201 and r.json().get("status") == "OTP_SENT"
    check("P10 tạo giao dịch -> 201 OTP_SENT (chưa trừ tiền)",
          ok and balance(1) == SEED_BALANCE[1], api_error(r) if not ok else f"pid={r.json()['payment_id']}")
    pid1 = r.json()["payment_id"]

    check("P11 tuition đã khóa PAYING sau khi tạo gd", tuition_status(tid1) == "PAYING")
    check("P12 email OTP đã ghi outbox (1 dòng PAYER)", outbox_count(pid1) == 1)

    code = active_otp_code(pid1)
    r = httpx.post(f"{GW}/payments/{pid1}/verify-otp", timeout=30,
                   headers=headers1, json={"otp": "000000"})
    check("P13 sai OTP -> 400 OTP_INVALID còn số lần thử",
          r.status_code == 400 and r.json()["error"]["code"] == "OTP_INVALID", api_error(r))

    r = httpx.post(f"{GW}/payments/{pid1}/verify-otp", timeout=30,
                   headers=headers1, json={"otp": code})
    ok = r.status_code == 200 and r.json().get("status") == "SUCCESS"
    check("P14 verify OTP đúng -> SUCCESS, balance_after trả về",
          ok and r.json().get("balance_after") == SEED_BALANCE[1] - amount1, api_error(r) if not ok else "")

    check("P15 tiền đã trừ đúng (DB payer)", balance(1) == SEED_BALANCE[1] - amount1)
    check("P16 tuition -> PAID", tuition_status(tid1) == "PAID")
    prow = payment_row(pid1)
    check("P17 payment SUCCESS + completed_at", prow.status == "SUCCESS" and prow.completed_at is not None)
    check("P18 email xác nhận 2 dòng (PAYER + SCHOOL)", outbox_count(pid1) == 3)
    with connect("PaymentDB") as c:
        hist = [row.to_status for row in c.execute(
            "SELECT to_status FROM dbo.payment_history WHERE payment_id = ? ORDER BY history_id",
            pid1)]
    check("P19 history đủ chuỗi FSM PENDING→OTP_SENT→PROCESSING→SUCCESS",
          hist == ["PENDING", "OTP_SENT", "PROCESSING", "SUCCESS"], str(hist))

    r = httpx.post(f"{GW}/payments/{pid1}/verify-otp", timeout=30,
                   headers=headers1, json={"otp": code})
    check("P20 verify lần 2 gd đã SUCCESS -> 409",
          r.status_code == 409, api_error(r))

    r = httpx.post(f"{GW}/payments", timeout=30, headers=headers1, json={"tuition_id": tid1})
    check("P21 tạo gd cho học phí đã PAID -> 409 TUITION_ALREADY_PAID",
          r.status_code == 409 and r.json()["error"]["code"] == "TUITION_ALREADY_PAID", api_error(r))

    # ---------- P2x: sai OTP đủ 5 lần -> LOCKED + bù trừ (uid2) ----------
    tuition2 = first_unpaid_tuition(tok2)
    tid2 = tuition2["tuition_id"]
    headers2 = {"Authorization": f"Bearer {tok2}"}
    r = httpx.post(f"{GW}/payments", timeout=30, headers=headers2, json={"tuition_id": tid2})
    pid2 = r.json()["payment_id"]
    check("P22 uid2 tạo gd thành công", r.status_code == 201, api_error(r))

    last = None
    for _ in range(5):
        last = httpx.post(f"{GW}/payments/{pid2}/verify-otp", timeout=30,
                          headers=headers2, json={"otp": "111111"})
    check("P23 sai 5 lần -> lần cuối 400 OTP_LOCKED",
          last.status_code == 400 and last.json()["error"]["code"] == "OTP_LOCKED", api_error(last))
    prow = payment_row(pid2)
    check("P24 gd FAILED reason OTP_LOCKED + tuition mở khóa + tiền không đổi",
          prow.status == "FAILED" and prow.failure_reason == "OTP_LOCKED"
          and tuition_status(tid2) == "UNPAID" and balance(2) == SEED_BALANCE[2])

    # ---------- P3x: thiếu dư -> 422 + bù trừ (uid3: dư 1tr, nợ 5tr) ----------
    tuition3 = first_unpaid_tuition(tok3)
    tid3 = tuition3["tuition_id"]
    headers3 = {"Authorization": f"Bearer {tok3}"}
    r = httpx.post(f"{GW}/payments", timeout=30, headers=headers3, json={"tuition_id": tid3})
    pid3 = r.json()["payment_id"]
    code3 = active_otp_code(pid3)
    r = httpx.post(f"{GW}/payments/{pid3}/verify-otp", timeout=30,
                   headers=headers3, json={"otp": code3})
    check("P30 uid3 đủ OTP nhưng thiếu dư -> 422 INSUFFICIENT_BALANCE",
          r.status_code == 422 and r.json()["error"]["code"] == "INSUFFICIENT_BALANCE", api_error(r))
    prow = payment_row(pid3)
    check("P31 gd FAILED reason CAPTURE_* + tuition UNPAID + tiền không đổi",
          prow.status == "FAILED" and prow.failure_reason == "CAPTURE_INSUFFICIENT_BALANCE"
          and tuition_status(tid3) == "UNPAID" and balance(3) == SEED_BALANCE[3])

    # ---------- P4x: BR-07 + phân quyền + idempotency ----------
    r = httpx.post(f"{GW}/payments", timeout=30, headers=headers3, json={"tuition_id": tid3})
    pid4 = r.json()["payment_id"]
    r = httpx.post(f"{GW}/payments", timeout=30, headers=headers3,
                   json={"tuition_id": tid3})
    check("P40 BR-07: 2 gd active cùng uid -> 409",
          r.status_code == 409, api_error(r))

    r = httpx.post(f"{GW}/payments/{pid4}/verify-otp", timeout=30,
                   headers=headers1, json={"otp": "123456"})
    check("P41 verify gd của người khác -> 403 FORBIDDEN",
          r.status_code == 403 and r.json()["error"]["code"] == "FORBIDDEN", api_error(r))

    r = httpx.post(f"{GW}/payments", timeout=30, headers=headers3,
                   json={"tuition_id": 99999})
    check("P42 học phí không tồn tại -> 404",
          r.status_code == 404, api_error(r))

    idem3 = {"Authorization": f"Bearer {tok3}", "Idempotency-Key": "test-idem-key-P43"}
    ra = httpx.post(f"{GW}/payments", timeout=30, headers=idem3, json={"tuition_id": tid3})
    # uid3 đang có gd active (pid4) nên bị chặn — đúng BR-07, chưa tới nhánh idempotency
    check("P43a gd active chặn tạo mới (409)", ra.status_code == 409, api_error(ra))

    # Kết thúc gd active của uid3 bằng cách dọn trực tiếp để test idempotency sạch
    reset_seed()
    rb = httpx.post(f"{GW}/payments", timeout=30, headers=idem3, json={"tuition_id": tid3})
    rc = httpx.post(f"{GW}/payments", timeout=30, headers=idem3, json={"tuition_id": tid3})
    check("P43 retry cùng Idempotency-Key -> cùng payment_id, idempotent=True",
          rb.status_code == 201 and rc.status_code == 201
          and rb.json()["payment_id"] == rc.json()["payment_id"]
          and rc.json().get("idempotent") is True,
          f"{rb.json().get('payment_id')} vs {rc.json().get('payment_id')}")

    # ---------- dọn dẹp ----------
    reset_seed()
    check("P99 reset dữ liệu về seed sau khi test",
          balance(1) == SEED_BALANCE[1] and tuition_status(tid1) == "UNPAID")

    print("=" * 64)
    passed = sum(_results)
    print(f"KẾT QUẢ: {passed}/{len(_results)} PASS, {len(_results) - passed} FAIL")
    print("=" * 64)
    sys.exit(0 if passed == len(_results) else 1)


if __name__ == "__main__":
    main()

"""Bộ test riêng cho notification-service (:8006) — TASK-A phần 2, BR-14.

Hai chế độ (tự phát hiện qua /health):
    - dry-run: chưa cấu hình GMAIL_USER trong services/.env → kiểm tra logic +
      dòng outbox, KHÔNG gửi mail thật.
    - smtp: đã cấu hình Gmail App Password → gửi email THẬT tới hộp thư
      NOTIF_TEST_TO_EMAIL (mặc định email của tài khoản 521H0092) — kiểm tra tay.

Yêu cầu: notification-service đang chạy ở :8006.
    python -m uvicorn main:app --port 8006 --app-dir services/notification-service

Chạy từ thư mục gốc:
    python scripts/test_notification.py
"""
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "services"))
from shared import config  # noqa: E402
from shared.db import connect  # noqa: E402

NOTIF = "http://localhost:8006"
INTERNAL = {"X-Internal-Token": config.INTERNAL_TOKEN}
PID_BASE = 990000000   # payment_id ảo để không đụng dữ liệu thật

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


def outbox_rows(payment_id: int):
    with connect("NotificationDB") as c:
        return c.execute(
            "SELECT to_email, recipient_type, template, status, attempts, last_error "
            "FROM dbo.email_outbox WHERE payment_id = ? ORDER BY outbox_id",
            payment_id,
        ).fetchall()


def main():
    print("=" * 64)
    print("TEST NOTIFICATION SERVICE — iBanking Tuition Payment (:8006)")
    print("=" * 64)

    try:
        r = httpx.get(f"{NOTIF}/health", timeout=5)
        assert r.status_code == 200
    except Exception:
        print("❌ FAIL  Không kết nối được notification-service :8006 — đã khởi động chưa?")
        sys.exit(1)
    mode = r.json().get("mode", "?")
    check("N01 /health", r.json().get("status") == "ok", f"mode={mode}")
    if mode == "dry-run":
        print(">>> Đang chạy DRY RUN (chưa cấu hình GMAIL_USER) — test logic + outbox.")
        print(">>> Muốn gửi mail thật: điền GMAIL_USER + GMAIL_APP_PASSWORD vào services/.env")

    # ---------- otp-email ----------
    pid1 = PID_BASE + 1
    r = httpx.post(f"{NOTIF}/internal/notifications/otp-email", timeout=30, headers=INTERNAL,
                   json={"payment_id": pid1, "to_email": "student@example.com",
                         "to_name": "Nguyen Van A", "otp_code": "482913", "expires_in": 300})
    ok = r.status_code == 200 and r.json().get("sent") is True
    check("N02 otp-email -> 200 sent", ok, api_error(r))
    rows = outbox_rows(pid1)
    check("N03 outbox: 1 dòng PAYER/OTP_EMAIL status SENT",
          len(rows) == 1 and rows[0].recipient_type == "PAYER"
          and rows[0].template == "OTP_EMAIL" and rows[0].status == "SENT")

    r = httpx.post(f"{NOTIF}/internal/notifications/otp-email", timeout=30, headers=INTERNAL,
                   json={"payment_id": pid1, "to_email": "khong-dung-dinh-dang",
                         "to_name": "A", "otp_code": "482913", "expires_in": 300})
    check("N04 otp-email sai định dạng email -> 400 VALIDATION_ERROR",
          r.status_code == 400 and r.json()["error"]["code"] == "VALIDATION_ERROR", api_error(r))

    # ---------- confirm-email ----------
    pid2 = PID_BASE + 2
    r = httpx.post(f"{NOTIF}/internal/notifications/confirm-email", timeout=30, headers=INTERNAL,
                   json={"payment_id": pid2, "to_email": "student@example.com",
                         "to_name": "Nguyen Van A", "cc_school_email": "finance@tdtu.edu.vn",
                         "amount": 7000000, "student_id": "521H0092", "tuition_id": 1,
                         "completed_at": "2026-09-10T15:30:00Z"})
    ok = r.status_code == 200 and r.json().get("sent") is True
    check("N05 confirm-email -> 200 sent (BR-14)", ok, api_error(r))
    rows = outbox_rows(pid2)
    ok = (len(rows) == 2
          and rows[0].recipient_type == "PAYER" and rows[0].status == "SENT"
          and rows[1].recipient_type == "SCHOOL" and rows[1].to_email == "finance@tdtu.edu.vn"
          and rows[1].status == "SENT"
          and all(rw.template == "CONFIRM_EMAIL" for rw in rows))
    check("N06 outbox: 2 dòng PAYER + SCHOOL đều SENT", ok)

    # ---------- bảo mật ----------
    r = httpx.post(f"{NOTIF}/internal/notifications/otp-email", timeout=10,
                   json={"payment_id": pid1, "to_email": "a@b.com", "to_name": "A",
                         "otp_code": "482913", "expires_in": 300})
    check("N07 thiếu X-Internal-Token -> 403 FORBIDDEN",
          r.status_code == 403 and r.json()["error"]["code"] == "FORBIDDEN", api_error(r))

    r = httpx.post(f"{NOTIF}/internal/notifications/confirm-email", timeout=10, headers=INTERNAL,
                   json={"payment_id": pid2, "to_email": "student@example.com",
                         "to_name": "A", "cc_school_email": "finance@tdtu.edu.vn",
                         "amount": -5, "student_id": "521H0092", "tuition_id": 1,
                         "completed_at": "2026-09-10T15:30:00Z"})
    check("N08 amount âm -> 422 validation", r.status_code == 422, api_error(r))

    if mode == "smtp":
        print("\n>>> Chế độ SMTP THẬT — kiểm tra hộp thư của bạn có 2 email vừa gửi.")

    # ---------- dọn dẹp ----------
    with connect("NotificationDB") as c:
        c.execute("DELETE FROM dbo.email_outbox WHERE payment_id >= ?", PID_BASE)
    check("N09 dọn bản ghi outbox test", True)

    print("=" * 64)
    passed = sum(_results)
    total = len(_results)
    print(f"KẾT QUẢ: {passed}/{total} PASS, {total - passed} FAIL")
    print("=" * 64)
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()

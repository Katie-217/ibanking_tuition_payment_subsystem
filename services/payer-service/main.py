"""payer-service (:8002) — thông tin người nộp tiền + số dư + trừ/hoàn tiền.

Port mặc định: 8002. Chạy:
    python -m uvicorn main:app --port 8002 --app-dir services/payer-service --reload
"""
import pyodbc
from fastapi import Depends, FastAPI
from pydantic import BaseModel, Field

from shared.db import connect, is_unique_violation
from shared.errors import (
    install_error_handlers, insufficient_balance, not_found,
    service_unavailable, state_conflict,
)
from shared.security import require_internal, require_uid

app = FastAPI(title="payer-service", version="1.1")
install_error_handlers(app)


# ------------------------- API người dùng -------------------------
@app.get("/health")
def health():
    try:
        with connect("PayerDB") as c:
            c.execute("SELECT 1").fetchone()
        return {"status": "ok", "service": "payer-service"}
    except pyodbc.Error:
        raise service_unavailable("Không kết nối được database PayerDB")


@app.get("/payers/me")
def payers_me(uid: int = Depends(require_uid)):
    """Thông tin người nộp tiền của CHÍNH user đăng nhập (uid từ JWT) — BR-04."""
    with connect("PayerDB") as c:
        row = c.execute(
            """
            SELECT p.payer_uid, p.full_name, p.phone, p.email, a.available_balance, a.currency
            FROM dbo.payers p
            JOIN dbo.accounts a ON a.payer_uid = p.payer_uid
            WHERE p.payer_uid = ?
            """,
            uid,
        ).fetchone()
    if row is None:
        raise not_found("Không tìm thấy hồ sơ người nộp tiền cho tài khoản này")
    return {
        "payer_uid": row.payer_uid,
        "full_name": row.full_name,
        "phone": row.phone,
        "email": row.email,
        "available_balance": int(row.available_balance),
        "currency": row.currency.strip() if row.currency else "VND",
    }


# ------------------------- API nội bộ (payment-service gọi) -------------------------
@app.get("/internal/payers/{uid}")
def internal_get_payer(uid: int, _: None = Depends(require_internal)):
    """payment-service đọc hồ sơ payer + số dư (email người nhận OTP) — docs/03 mục 3.1."""
    with connect("PayerDB") as c:
        row = c.execute(
            """
            SELECT p.payer_uid, p.full_name, p.phone, p.email, a.available_balance, a.currency
            FROM dbo.payers p
            JOIN dbo.accounts a ON a.payer_uid = p.payer_uid
            WHERE p.payer_uid = ?
            """,
            uid,
        ).fetchone()
    if row is None:
        raise not_found("Không tìm thấy hồ sơ người nộp tiền")
    return {
        "payer_uid": row.payer_uid,
        "full_name": row.full_name,
        "phone": row.phone,
        "email": row.email,
        "available_balance": int(row.available_balance),
        "currency": row.currency.strip() if row.currency else "VND",
    }


class BalanceRequest(BaseModel):
    payment_id: int
    uid: int
    amount: int = Field(gt=0)


def _find_ledger(c: pyodbc.Connection, payment_id: int, change_type: str):
    return c.execute(
        "SELECT amount, balance_after FROM dbo.balance_ledger WHERE payment_id = ? AND change_type = ?",
        payment_id, change_type,
    ).fetchone()


def _current_balance(c: pyodbc.Connection, uid: int) -> int:
    row = c.execute("SELECT available_balance FROM dbo.accounts WHERE payer_uid = ?", uid).fetchone()
    if row is None:
        raise not_found("Không tìm thấy tài khoản của người nộp tiền")
    return int(row.available_balance)


@app.post("/internal/balance/capture")
def capture(body: BalanceRequest, _: None = Depends(require_internal)):
    """Trừ tiền NGUYÊN TỬ: 1 câu UPDATE có điều kiện balance >= amount (Case A — chống dư âm).

    Idempotent theo payment_id: gọi lại lần 2 không trừ thêm (BR-10, uq_ledger_idem).
    """
    with connect("PayerDB") as c:
        existing = _find_ledger(c, body.payment_id, "CAPTURE")
        if existing is not None:
            return {"captured": True, "idempotent": True, "balance_after": int(existing.balance_after)}

        cur = c.execute(
            "UPDATE dbo.accounts SET available_balance = available_balance - ? "
            "WHERE payer_uid = ? AND available_balance >= ?",
            body.amount, body.uid, body.amount,
        )
        if cur.rowcount == 0:
            acc = c.execute(
                "SELECT available_balance FROM dbo.accounts WHERE payer_uid = ?", body.uid
            ).fetchone()
            raise insufficient_balance(body.amount, int(acc.available_balance) if acc else 0)

        acc = c.execute(
            "SELECT account_id, available_balance FROM dbo.accounts WHERE payer_uid = ?", body.uid
        ).fetchone()
        try:
            c.execute(
                "INSERT INTO dbo.balance_ledger (account_id, payment_id, change_type, amount, balance_after) "
                "VALUES (?, ?, N'CAPTURE', ?, ?)",
                acc.account_id, body.payment_id, body.amount, acc.available_balance,
            )
        except pyodbc.IntegrityError as exc:
            if not is_unique_violation(exc):
                raise
            # 2 request capture trùng payment_id chạy song song: request thua bị rollback toàn bộ
            raise state_conflict("payment_id đã được trừ tiền bởi giao dịch khác")

    return {"captured": True, "balance_after": int(acc.available_balance)}


@app.post("/internal/balance/release")
def release(body: BalanceRequest, _: None = Depends(require_internal)):
    """Hoàn tiền bù trừ. Idempotent theo payment_id.

    An toàn tiền: CHỈ hoàn khi payment_id đã thật sự bị trừ (có chứng từ CAPTURE trong ledger).
    Giao dịch hủy/hết hạn lúc chưa trừ tiền (còn PENDING/OTP_SENT) → không cộng gì, tránh
    tạo tiền từ không khí.
    """
    with connect("PayerDB") as c:
        existing = _find_ledger(c, body.payment_id, "RELEASE")
        if existing is not None:
            return {"released": True, "idempotent": True, "balance_after": int(existing.balance_after)}

        captured = _find_ledger(c, body.payment_id, "CAPTURE")
        if captured is None:
            return {
                "released": False, "skipped": True, "reason": "NOT_CAPTURED",
                "balance_after": _current_balance(c, body.uid),
            }
        if int(captured.amount) != body.amount:
            raise state_conflict(
                "Số tiền hoàn không khớp số tiền đã trừ của giao dịch này"
            )

        acc = c.execute(
            "SELECT account_id FROM dbo.accounts WHERE payer_uid = ?", body.uid
        ).fetchone()
        if acc is None:
            raise not_found("Không tìm thấy tài khoản của người nộp tiền")

        c.execute(
            "UPDATE dbo.accounts SET available_balance = available_balance + ? WHERE payer_uid = ?",
            body.amount, body.uid,
        )
        new_balance = c.execute(
            "SELECT available_balance FROM dbo.accounts WHERE payer_uid = ?", body.uid
        ).fetchone()
        try:
            c.execute(
                "INSERT INTO dbo.balance_ledger (account_id, payment_id, change_type, amount, balance_after) "
                "VALUES (?, ?, N'RELEASE', ?, ?)",
                acc.account_id, body.payment_id, body.amount, new_balance.available_balance,
            )
        except pyodbc.IntegrityError as exc:
            if not is_unique_violation(exc):
                raise
            raise state_conflict("payment_id đã được hoàn tiền trước đó")

    return {"released": True, "balance_after": int(new_balance.available_balance)}
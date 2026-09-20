from fastapi import Depends, FastAPI
from pydantic import BaseModel, Field

from shared.db import get_db, is_unique_violation
from shared.errors import (
    install_error_handlers, insufficient_balance, not_found,
    service_unavailable, state_conflict,
)
from shared.security import require_internal, require_uid
from shared.models.payer_models import PayerProfileReadModel, AccountBalanceWriteModel, BalanceLedgerWriteModel

app = FastAPI(title="payer-service", version="1.1")
install_error_handlers(app)


class BalanceRequest(BaseModel):
    payment_id: str | int
    uid: int
    amount: float = Field(gt=0)


@app.get("/health")
def health():
    try:
        db = get_db("payer_db")
        db.command("ping")
        return {"status": "ok", "service": "payer-service", "database": "payer_db (MongoDB)"}
    except Exception as e:
        raise service_unavailable(f"Không kết nối được MongoDB payer_db: {str(e)}")


@app.get("/payers/me", response_model=PayerProfileReadModel)
def payers_me(uid: int = Depends(require_uid)):
    db = get_db("payer_db")
    payer_doc = db.payers.find_one({"payer_uid": uid})
    account_doc = db.accounts.find_one({"payer_uid": uid})

    if not payer_doc or not account_doc:
        raise not_found("Không tìm thấy hồ sơ người nộp tiền cho tài khoản này")

    return PayerProfileReadModel(
        payer_uid=payer_doc["payer_uid"],
        full_name=payer_doc["full_name"],
        phone=payer_doc.get("phone"),
        email=payer_doc["email"],
        available_balance=float(account_doc["available_balance"]),
        currency=account_doc.get("currency", "VND")
    )


@app.get("/internal/payers/{uid}", response_model=PayerProfileReadModel)
def internal_get_payer(uid: int, _: None = Depends(require_internal)):
    db = get_db("payer_db")
    payer_doc = db.payers.find_one({"payer_uid": uid})
    account_doc = db.accounts.find_one({"payer_uid": uid})

    if not payer_doc or not account_doc:
        raise not_found("Không tìm thấy hồ sơ người nộp tiền")

    return PayerProfileReadModel(
        payer_uid=payer_doc["payer_uid"],
        full_name=payer_doc["full_name"],
        phone=payer_doc.get("phone"),
        email=payer_doc["email"],
        available_balance=float(account_doc["available_balance"]),
        currency=account_doc.get("currency", "VND")
    )


@app.post("/internal/balance/capture")
def capture(body: BalanceRequest, _: None = Depends(require_internal)):
    db = get_db("payer_db")
    payment_id_str = str(body.payment_id)

    # Kiểm tra Idempotency
    existing = db.balance_ledger.find_one({"payment_id": payment_id_str, "change_type": "CAPTURE"})
    if existing:
        return {"captured": True, "idempotent": True, "balance_after": float(existing["balance_after"])}

    # Atomic Update với MongoDB find_one_and_update
    account = db.accounts.find_one({"payer_uid": body.uid})
    if not account:
        raise not_found("Không tìm thấy tài khoản người nộp tiền")

    current_balance = float(account["available_balance"])
    if current_balance < body.amount:
        raise insufficient_balance(body.amount, current_balance)

    updated_account = db.accounts.find_one_and_update(
        {"payer_uid": body.uid, "available_balance": {"$gte": body.amount}},
        {"$inc": {"available_balance": -body.amount}},
        return_document=True
    )

    if not updated_account:
        # Re-fetch balance
        acc = db.accounts.find_one({"payer_uid": body.uid})
        bal = float(acc["available_balance"]) if acc else 0.0
        raise insufficient_balance(body.amount, bal)

    new_balance = float(updated_account["available_balance"])

    # Sử dụng Write Model ghi nhận Ledger
    ledger = BalanceLedgerWriteModel(
        account_id=str(updated_account.get("account_id", updated_account["_id"])),
        payment_id=payment_id_str,
        change_type="CAPTURE",
        amount=body.amount,
        balance_after=new_balance
    )

    try:
        db.balance_ledger.insert_one(ledger.model_dump())
    except Exception as exc:
        if is_unique_violation(exc):
            raise state_conflict("payment_id đã được trừ tiền bởi giao dịch khác")

    return {"captured": True, "balance_after": new_balance}


@app.post("/internal/balance/release")
def release(body: BalanceRequest, _: None = Depends(require_internal)):
    db = get_db("payer_db")
    payment_id_str = str(body.payment_id)

    # Idempotency check
    existing = db.balance_ledger.find_one({"payment_id": payment_id_str, "change_type": "RELEASE"})
    if existing:
        return {"released": True, "idempotent": True, "balance_after": float(existing["balance_after"])}

    captured = db.balance_ledger.find_one({"payment_id": payment_id_str, "change_type": "CAPTURE"})
    if not captured:
        account = db.accounts.find_one({"payer_uid": body.uid})
        bal = float(account["available_balance"]) if account else 0.0
        return {
            "released": False, "skipped": True, "reason": "NOT_CAPTURED",
            "balance_after": bal
        }

    if float(captured["amount"]) != body.amount:
        raise state_conflict("Số tiền hoàn không khớp số tiền đã trừ của giao dịch này")

    updated_account = db.accounts.find_one_and_update(
        {"payer_uid": body.uid},
        {"$inc": {"available_balance": body.amount}},
        return_document=True
    )

    if not updated_account:
        raise not_found("Không tìm thấy tài khoản người nộp tiền để hoàn tiền")

    new_balance = float(updated_account["available_balance"])

    ledger = BalanceLedgerWriteModel(
        account_id=str(updated_account.get("account_id", updated_account["_id"])),
        payment_id=payment_id_str,
        change_type="RELEASE",
        amount=body.amount,
        balance_after=new_balance
    )

    try:
        db.balance_ledger.insert_one(ledger.model_dump())
    except Exception as exc:
        if is_unique_violation(exc):
            raise state_conflict("payment_id đã được hoàn tiền trước đó")

    return {"released": True, "balance_after": new_balance}

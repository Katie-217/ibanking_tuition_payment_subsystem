#!/usr/bin/env python3
"""
Script Khởi Tạo & Seed Data Cho MongoDB (Database-per-Service Architecture)
Tự động tạo 6 Databases: auth_db, payer_db, tuition_db, payment_db, otp_db, notification_db
Cấu hình sẵn 2 tài khoản sinh viên thử nghiệm:
1. 521H0092 - Võ Thị Thiên Kim
2. 523H0058 - Phạm Huỳnh Trịnh Nam
"""

import os
import sys
from datetime import datetime, timezone
import bcrypt
from pymongo import MongoClient, ASCENDING

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_PREFIX = os.getenv("MONGO_DB_PREFIX", "")

def get_db_name(name: str) -> str:
    return f"{MONGO_DB_PREFIX}{name}" if MONGO_DB_PREFIX else name

def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def init_all():
    print(f"[*] Connecting to MongoDB at {MONGO_URI} ...")
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)

    # -----------------------------------------------------------------
    # 1. AUTH DB (auth_db)
    # -----------------------------------------------------------------
    auth_db = client[get_db_name("auth_db")]
    print("[+] Initializing auth_db ...")
    auth_db.users.create_index([("uid", ASCENDING)], unique=True)
    auth_db.users.create_index([("username", ASCENDING)], unique=True)
    auth_db.credentials.create_index([("uid", ASCENDING)], unique=True)

    default_password_hash = hash_password("Password123@")

    users_data = [
        {
            "uid": 5210092,
            "username": "521H0092",
            "full_name": "Võ Thị Thiên Kim",
            "phone": "0901234567",
            "email": "521h0092@student.tdtu.edu.vn",
            "role": "student",
            "status": "ACTIVE",
            "created_at": datetime.now(timezone.utc)
        },
        {
            "uid": 5230058,
            "username": "523H0058",
            "full_name": "Phạm Huỳnh Trịnh Nam",
            "phone": "0908765432",
            "email": "523h0058@student.tdtu.edu.vn",
            "role": "student",
            "status": "ACTIVE",
            "created_at": datetime.now(timezone.utc)
        }
    ]

    for u in users_data:
        auth_db.users.update_one({"uid": u["uid"]}, {"$set": u}, upsert=True)
        cred = {
            "uid": u["uid"],
            "password_hash": default_password_hash,
            "updated_at": datetime.now(timezone.utc)
        }
        auth_db.credentials.update_one({"uid": u["uid"]}, {"$set": cred}, upsert=True)

    print("  -> Users seeded: 521H0092 (Võ Thị Thiên Kim), 523H0058 (Phạm Huỳnh Trịnh Nam)")

    # -----------------------------------------------------------------
    # 2. PAYER DB (payer_db)
    # -----------------------------------------------------------------
    payer_db = client[get_db_name("payer_db")]
    print("[+] Initializing payer_db ...")
    payer_db.payers.create_index([("payer_uid", ASCENDING)], unique=True)
    payer_db.accounts.create_index([("payer_uid", ASCENDING)], unique=True)
    payer_db.balance_ledger.create_index([("account_id", ASCENDING)])

    payers_data = [
        {
            "payer_uid": 5210092,
            "full_name": "Võ Thị Thiên Kim",
            "phone": "0901234567",
            "email": "521h0092@student.tdtu.edu.vn"
        },
        {
            "payer_uid": 5230058,
            "full_name": "Phạm Huỳnh Trịnh Nam",
            "phone": "0908765432",
            "email": "523h0058@student.tdtu.edu.vn"
        }
    ]
    accounts_data = [
        {
            "account_id": "ACC_5210092",
            "payer_uid": 5210092,
            "available_balance": 15000000.0,
            "currency": "VND",
            "updated_at": datetime.now(timezone.utc)
        },
        {
            "account_id": "ACC_5230058",
            "payer_uid": 5230058,
            "available_balance": 20000000.0,
            "currency": "VND",
            "updated_at": datetime.now(timezone.utc)
        }
    ]

    for p in payers_data:
        payer_db.payers.update_one({"payer_uid": p["payer_uid"]}, {"$set": p}, upsert=True)
    for a in accounts_data:
        payer_db.accounts.update_one({"payer_uid": a["payer_uid"]}, {"$set": a}, upsert=True)

    print("  -> Payers and initial account balances seeded (15M VND & 20M VND)")

    # -----------------------------------------------------------------
    # 3. TUITION DB (tuition_db)
    # -----------------------------------------------------------------
    tuition_db = client[get_db_name("tuition_db")]
    print("[+] Initializing tuition_db ...")
    tuition_db.schools.create_index([("school_id", ASCENDING)], unique=True)
    tuition_db.students.create_index([("student_id", ASCENDING)], unique=True)
    tuition_db.tuitions.create_index([("tuition_id", ASCENDING)], unique=True)
    tuition_db.tuitions.create_index([("student_id", ASCENDING)])

    school_info = {
        "school_id": "TDTU",
        "name": "Trường Đại học Tôn Đức Thắng",
        "finance_email": "tai-chinh@tdtu.edu.vn",
        "beneficiary_name": "TRUONG DAI HOC TON DUC THANG",
        "bank_name": "Ngân hàng TMCP Công thương Việt Nam (VietinBank) - CN Nam Sài Gòn",
        "bank_account_no": "118000045678"
    }
    tuition_db.schools.update_one({"school_id": "TDTU"}, {"$set": school_info}, upsert=True)

    tuitions_seed = [
        {
            "tuition_id": "TUI_521H0092_20241",
            "student_id": "521H0092",
            "student_name": "Võ Thị Thiên Kim",
            "school_id": "TDTU",
            "school_name": "Trường Đại học Tôn Đức Thắng",
            "finance_email": "tai-chinh@tdtu.edu.vn",
            "beneficiary_name": "TRUONG DAI HOC TON DUC THANG",
            "bank_name": "VietinBank - CN Nam Sài Gòn",
            "bank_account_no": "118000045678",
            "academic_year": "2024-2025",
            "semester": "Học kỳ 1",
            "total_amount": 8450000.0,
            "status": "UNPAID",
            "items": [
                {"subject_code": "503001", "subject_name": "Lập trình Python nâng cao", "credits": 3, "amount": 2250000.0},
                {"subject_code": "503002", "subject_name": "Kiến trúc Microservices & Cloud", "credits": 4, "amount": 3000000.0},
                {"subject_code": "503003", "subject_name": "Cơ sở dữ liệu NoSQL", "credits": 3, "amount": 2250000.0},
                {"subject_code": "503004", "subject_name": "Quản lý dự án phần mềm", "credits": 2, "amount": 950000.0}
            ],
            "created_at": datetime.now(timezone.utc)
        },
        {
            "tuition_id": "TUI_523H0058_20241",
            "student_id": "523H0058",
            "student_name": "Phạm Huỳnh Trịnh Nam",
            "school_id": "TDTU",
            "school_name": "Trường Đại học Tôn Đức Thắng",
            "finance_email": "tai-chinh@tdtu.edu.vn",
            "beneficiary_name": "TRUONG DAI HOC TON DUC THANG",
            "bank_name": "VietinBank - CN Nam Sài Gòn",
            "bank_account_no": "118000045678",
            "academic_year": "2024-2025",
            "semester": "Học kỳ 1",
            "total_amount": 6200000.0,
            "status": "UNPAID",
            "items": [
                {"subject_code": "503005", "subject_name": "Phát triển phần mềm Hướng dịch vụ (SOA)", "credits": 3, "amount": 2400000.0},
                {"subject_code": "503006", "subject_name": "An toàn thông tin & Mã hóa", "credits": 3, "amount": 2400000.0},
                {"subject_code": "503007", "subject_name": "Thực hành Microservices với Docker", "credits": 2, "amount": 1400000.0}
            ],
            "created_at": datetime.now(timezone.utc)
        }
    ]

    for t in tuitions_seed:
        tuition_db.tuitions.update_one({"tuition_id": t["tuition_id"]}, {"$set": t}, upsert=True)

    print("  -> Tuitions seeded (8.45M VND for Võ Thị Thiên Kim & 6.2M VND for Phạm Huỳnh Trịnh Nam)")

    # -----------------------------------------------------------------
    # 4. PAYMENT DB (payment_db)
    # -----------------------------------------------------------------
    payment_db = client[get_db_name("payment_db")]
    print("[+] Initializing payment_db ...")
    payment_db.payments.create_index([("payment_id", ASCENDING)], unique=True)
    payment_db.payments.create_index([("uid", ASCENDING)])
    payment_db.payment_histories.create_index([("payment_id", ASCENDING)], unique=True)

    # -----------------------------------------------------------------
    # 5. OTP DB (otp_db)
    # -----------------------------------------------------------------
    otp_db = client[get_db_name("otp_db")]
    print("[+] Initializing otp_db ...")
    otp_db.otps.create_index([("otp_id", ASCENDING)], unique=True)
    otp_db.otps.create_index([("payment_id", ASCENDING)])

    # -----------------------------------------------------------------
    # 6. NOTIFICATION DB (notification_db)
    # -----------------------------------------------------------------
    notification_db = client[get_db_name("notification_db")]
    print("[+] Initializing notification_db ...")
    notification_db.email_logs.create_index([("created_at", ASCENDING)])

    print("\n[SUCCESS] All 6 MongoDB databases initialized & seeded successfully!")

if __name__ == "__main__":
    try:
        init_all()
    except Exception as e:
        print(f"[ERROR] Failed to initialize MongoDB: {e}", file=sys.stderr)
        sys.exit(1)

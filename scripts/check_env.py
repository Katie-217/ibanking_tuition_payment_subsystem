import importlib
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "services"))

PASS, FAIL, WARN = "✅", "❌", "⚠️"

DATABASES = ["auth_db", "payer_db", "tuition_db", "payment_db", "otp_db", "notification_db"]
KEY_COLLECTIONS = {
    "auth_db": ["users", "credentials"],
    "payer_db": ["payers", "accounts"],
    "tuition_db": ["schools", "tuitions"],
    "payment_db": ["payments"],
    "otp_db": ["otps"],
    "notification_db": ["email_logs"],
}


def check_packages():
    print("1. Gói Python:")
    required = {
        "fastapi": "fastapi", "uvicorn": "uvicorn", "pymongo": "pymongo",
        "jwt": "PyJWT", "bcrypt": "bcrypt", "httpx": "httpx",
        "dotenv": "python-dotenv",
    }
    ok = True
    for mod, pkg in required.items():
        try:
            importlib.import_module(mod)
            print(f"   {PASS} {pkg}")
        except ImportError:
            print(f"   {FAIL} {pkg} chưa cài -> chạy: pip install -r services/requirements.txt")
            ok = False
    return ok


def check_dotenv():
    print("\n2. File .env & Cấu hình MongoDB:")
    from shared import config
    env_paths = [
        Path(__file__).resolve().parent.parent / "services" / ".env",
        Path(__file__).resolve().parent.parent / ".env",
    ]
    found = [p for p in env_paths if p.exists()]
    if found:
        print(f"   {PASS} Có .env: {found[0]}")
    else:
        print(f"   {WARN} Không có .env, sử dụng cấu hình mặc định (MongoDB: {config.MONGO_URI})")

    print(f"   {PASS} MONGO_URI: {config.MONGO_URI}")
    return True


def check_databases():
    print("\n3. Kết nối 6 MongoDB Databases:")
    from shared.db import get_mongo_client, get_db

    all_ok = True
    try:
        client = get_mongo_client()
        client.admin.command("ping")
        print(f"   {PASS} Kết nối MongoDB Server thành công.")
    except Exception as exc:
        print(f"   {FAIL} Không kết nối được MongoDB: {exc}")
        print("        -> Đảm bảo MongoDB Service hoặc `docker compose up -d` đang chạy.")
        return False

    for db_name in DATABASES:
        try:
            db = get_db(db_name)
            colls = KEY_COLLECTIONS[db_name]
            counts = {}
            for c in colls:
                counts[c] = db[c].count_documents({})
            detail = ", ".join(f"{c}={counts[c]}" for c in colls)
            print(f"   {PASS} {db_name}: {detail}")
        except Exception as exc:
            all_ok = False
            print(f"   {FAIL} {db_name}: {exc}")

    return all_ok


def main():
    print("=" * 64)
    print("KIỂM TRA MÔI TRƯỜNG MONGODB & MICROSERVICES — iBanking Tuition Payment")
    print("=" * 64)
    results = [check_packages(), check_dotenv(), check_databases()]
    print("\n" + "=" * 64)
    if all(results):
        print(f"{PASS} Môi trường OK — Sẵn sàng khởi chạy Microservices!")
    else:
        print(f"{FAIL} Còn lỗi ở trên — chạy: python scripts/init_mongodb.py để nạp database.")
    print("=" * 64)
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()

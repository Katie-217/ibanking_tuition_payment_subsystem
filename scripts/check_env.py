"""Kiểm tra môi trường trước khi chạy API test.

Chạy từ thư mục gốc dự án:
    python scripts/check_env.py

Kiểm tra 5 mục:
  1. Các gói Python cần thiết (fastapi, pyodbc, PyJWT, bcrypt, httpx, dotenv)
  2. ODBC Driver 18 đã cài trên máy chưa
  3. File .env đã cấu hình (nhắc nếu đang dùng giá trị mặc định)
  4. Kết nối được 6 database + đếm số dòng các bảng quan trọng
  5. Mật khẩu demo đã sinh hash bcrypt chưa (không còn 'TO_BE_SET')
"""
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "services"))

PASS, FAIL, WARN = "✅", "❌", "⚠️"

DATABASES = ["AuthDB", "PayerDB", "TuitionDB", "PaymentDB", "OTPDB", "NotificationDB"]
KEY_TABLES = {
    "AuthDB": ["users", "user_credentials"],
    "PayerDB": ["payers", "accounts", "balance_ledger"],
    "TuitionDB": ["schools", "faculties", "majors", "edu_systems", "students", "tuitions"],
    "PaymentDB": ["payments", "payment_history"],
    "OTPDB": ["otps"],
    "NotificationDB": ["email_outbox"],
}


def check_packages():
    print("1. Gói Python:")
    required = {
        "fastapi": "fastapi", "uvicorn": "uvicorn", "pyodbc": "pyodbc",
        "jwt": "PyJWT", "bcrypt": "bcrypt", "httpx": "httpx",
        "dotenv": "python-dotenv",
    }
    ok = True
    buggy_pyjwt = False
    for mod, pkg in required.items():
        try:
            importlib.import_module(mod)
            print(f"   {PASS} {pkg}")
        except ImportError:
            print(f"   {FAIL} {pkg} chưa cài -> chạy: pip install -r services/requirements.txt")
            ok = False
    if ok:
        import jwt as pyjwt
        if not hasattr(pyjwt, "PyJWTError"):  # gói 'jwt' lỗi thời đè PyJWT
            buggy_pyjwt = True
            print(f"   {WARN} Đang dùng gói 'jwt' cũ (thiếu PyJWTError). Chạy: pip uninstall jwt")
    return ok and not buggy_pyjwt


def check_odbc():
    print("\n2. ODBC Driver:")
    try:
        import pyodbc
    except ImportError:
        print(f"   {FAIL} Chưa cài pyodbc nên chưa thể kiểm tra ODBC Driver.")
        return False
    try:
        drivers = [d for d in pyodbc.drivers() if "SQL Server" in d]
        if not drivers:
            print(f"   {FAIL} Không thấy ODBC Driver for SQL Server.")
            print("          Tải ODBC Driver 18: https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server")
            return False
        wanted = "ODBC Driver 18 for SQL Server"
        if wanted in drivers:
            print(f"   {PASS} {wanted}")
            return True
        print(f"   {WARN} Có {drivers} (không phải bản 18). Sửa DB_DRIVER trong .env cho khớp.")
        return True
    except ImportError:
        return False


def check_dotenv():
    print("\n3. File .env:")
    from shared import config
    env_paths = [
        Path(__file__).resolve().parent.parent / "services" / ".env",
        Path(__file__).resolve().parent.parent / ".env",
    ]
    found = [p for p in env_paths if p.exists()]
    if not found:
        print(f"   {FAIL} Chưa có .env -> copy services/.env.example thành services/.env rồi điền DB_PWD.")
        return False
    print(f"   {PASS} Có .env: {found[0]}")
    if not config.DB_PWD:
        print(f"   {WARN} DB_PWD trống — nếu SQL Server dùng Windows Auth thì bỏ qua, còn không phải điền mật khẩu sa.")
    if config.JWT_SECRET == "ibanking-demo-secret-change-me":
        print(f"   {WARN} JWT_SECRET đang là giá trị mặc định (chấp nhận được khi test local).")
    if config.INTERNAL_TOKEN == "internal-shared-secret":
        print(f"   {WARN} INTERNAL_TOKEN đang là giá trị mặc định (chấp nhận được khi test local).")
    return True


def check_databases():
    print("\n4. Kết nối 6 database:")
    try:
        import pyodbc
    except ImportError:
        print(f"   {FAIL} Chưa cài pyodbc — bỏ qua kiểm tra kết nối database.")
        return False
    from shared import config

    all_ok = True
    for db in DATABASES:
        try:
            conn = pyodbc.connect(config.db_dsn(db), timeout=5)
            tables = KEY_TABLES[db]
            counts = {}
            with conn.cursor() as cur:
                for t in tables:
                    if cur.tables(table=t, tableType="TABLE").fetchone():
                        counts[t] = cur.execute(f"SELECT COUNT(*) FROM dbo.[{t}]").fetchval()
                    else:
                        counts[t] = None
            conn.close()
            detail = ", ".join(f"{t}={counts[t] if counts[t] is not None else 'THIẾU'}" for t in tables)
            print(f"   {PASS} {db}: {detail}")
            if any(v is None for v in counts.values()):
                all_ok = False
                print(f"        {FAIL} Bảng thiếu -> chạy db/02-schema.sql")
        except pyodbc.Error as exc:
            all_ok = False
            print(f"   {FAIL} {db}: {str(exc).splitlines()[0]}")
            print("        -> Kiểm tra SQL Server đang chạy + .env đúng + đã chạy db/01-create-databases.sql")
    return all_ok


def check_password_hashes():
    print("\n5. Mật khẩu demo (bcrypt):")
    try:
        import pyodbc
    except ImportError:
        print(f"   {FAIL} Chưa cài pyodbc — bỏ qua kiểm tra password hash.")
        return False
    from shared import config

    try:
        conn = pyodbc.connect(config.db_dsn("AuthDB"), timeout=5)
        with conn.cursor() as cur:
            n = cur.execute("SELECT COUNT(*) FROM dbo.user_credentials WHERE password_hash = N'TO_BE_SET'").fetchval()
        conn.close()
        if n:
            print(f"   {FAIL} {n} tài khoản vẫn còn mật khẩu placeholder 'TO_BE_SET'.")
            print("          -> Chạy: python db/generate_password_hashes.py  (đặt PYTHONPATH=services nếu cần)")
            print("          -> Rồi dán các lệnh UPDATE in ra vào SSMS chạy.")
            return False
        print(f"   {PASS} Mật khẩu demo đã có hash bcrypt (đăng nhập được).")
        return True
    except pyodbc.Error:
        return False


def main():
    print("=" * 64)
    print("KIỂM TRA MÔI TRƯỜNG — iBanking Tuition Payment")
    print("=" * 64)
    results = [check_packages(), check_odbc(), check_dotenv(), check_databases(), check_password_hashes()]
    print("\n" + "=" * 64)
    if all(results):
        print(f"{PASS} Môi trường OK — chạy tiếp: scripts\\run_dev.bat rồi python scripts/test_api.py")
    else:
        print(f"{FAIL} Còn lỗi ở trên — sửa xong chạy lại: python scripts/check_env.py")
    print("=" * 64)
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
"""
BƯỚC 4: Sinh hash bcrypt cho mật khẩu demo (sau khi chạy 03-seed.sql).

Dùng:
    1. Mở terminal trong thư mục db/
    2. pip install bcrypt          (nếu chưa có)
    3. python generate_password_hashes.py
    4. Dán các dòng UPDATE in ra vào SSMS (database AuthDB) và chạy.

Mật khẩu demo mặc định: abc12345
"""
import bcrypt

# (username, mat_khau_demo) — không giả định giá trị uid tự tăng trong AuthDB.
USERS = [
    ("521H0092", "abc12345"),
    ("522H0145", "abc12345"),
    ("523H0201", "abc12345"),
]

def main() -> None:
    print("-- ===== Paste the lines below into SSMS (database AuthDB) ===== --")
    for username, password in USERS:
        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")
        print(
            f"UPDATE dbo.user_credentials SET password_hash = N'{hashed}' "
            f"WHERE uid = (SELECT uid FROM dbo.users WHERE username = N'{username}'); "
            f"-- {username} / {password}"
        )

if __name__ == "__main__":
    main()
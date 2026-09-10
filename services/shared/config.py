"""Cấu hình chung: đọc biến môi trường (ưu tiên file .env)."""
import os
from pathlib import Path

_ENV_FILES = [
    Path(__file__).resolve().parent.parent / ".env",          # services/.env
    Path(__file__).resolve().parent.parent.parent / ".env",   # <repo>/.env
]


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    for f in _ENV_FILES:
        if f.exists():
            load_dotenv(f, override=False)


_load_dotenv()


def get_env(key: str, default: str = "") -> str:
    return os.getenv(key, default)


def get_int_env(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, str(default)))
    except (TypeError, ValueError):
        return default


DB_SERVER = get_env("DB_SERVER", "localhost")
DB_UID = get_env("DB_UID", "sa")
DB_PWD = get_env("DB_PWD", "")
DB_DRIVER = get_env("DB_DRIVER", "ODBC Driver 18 for SQL Server")

JWT_SECRET = get_env("JWT_SECRET", "ibanking-demo-secret-change-me")
JWT_EXPIRES_MINUTES = get_int_env("JWT_EXPIRES_MINUTES", 30)
INTERNAL_TOKEN = get_env("INTERNAL_TOKEN", "internal-shared-secret")


def db_dsn(database: str) -> str:
    """Dựng chuỗi kết nối pyodbc cho 1 database cụ thể (Database per Service)."""
    if DB_UID:
        return (
            f"DRIVER={{{DB_DRIVER}}};SERVER={DB_SERVER};DATABASE={database};"
            f"UID={DB_UID};PWD={DB_PWD};Encrypt=yes;TrustServerCertificate=yes;"
        )
    return (
        f"DRIVER={{{DB_DRIVER}}};SERVER={DB_SERVER};DATABASE={database};"
        f"Trusted_Connection=yes;Encrypt=yes;TrustServerCertificate=yes;"
    )
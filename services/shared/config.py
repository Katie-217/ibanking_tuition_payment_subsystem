import os
from pathlib import Path

_ENV_FILES = [
    Path(__file__).resolve().parent.parent / ".env",
    Path(__file__).resolve().parent.parent.parent / ".env",
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

MONGO_URI = get_env("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_PREFIX = get_env("MONGO_DB_PREFIX", "")

JWT_SECRET = get_env("JWT_SECRET", "ibanking-demo-secret-change-me")
JWT_EXPIRES_MINUTES = get_int_env("JWT_EXPIRES_MINUTES", 30)
INTERNAL_TOKEN = get_env("INTERNAL_TOKEN", "internal-shared-secret")


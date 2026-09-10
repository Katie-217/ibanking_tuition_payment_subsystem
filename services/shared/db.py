"""Quản lý kết nối SQL Server (pyodbc).

connect() là context manager: commit khi thành công, rollback khi lỗi
— đảm bảo mọi thao tác transaction (trừ tiền, đổi trạng thái) là nguyên tử.
"""
from contextlib import contextmanager

import pyodbc

from .config import db_dsn


@contextmanager
def connect(database: str):
    conn = pyodbc.connect(db_dsn(database), timeout=10)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def is_unique_violation(exc: pyodbc.Error) -> bool:
    """Kiểm tra lỗi có phải vi phạm UNIQUE constraint (idempotency) hay không."""
    return exc.args and str(exc.args[0]).startswith("23000")
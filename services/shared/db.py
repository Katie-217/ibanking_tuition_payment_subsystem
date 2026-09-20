import pymongo
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

from .config import MONGO_URI, MONGO_DB_PREFIX

_client: MongoClient | None = None


def get_mongo_client() -> MongoClient:
    global _client
    if _client is None:
        _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    return _client


def get_db(db_name: str):
    client = get_mongo_client()
    full_name = f"{MONGO_DB_PREFIX}{db_name}" if MONGO_DB_PREFIX else db_name
    return client[full_name]


def is_unique_violation(exc: Exception) -> bool:
    return isinstance(exc, DuplicateKeyError)


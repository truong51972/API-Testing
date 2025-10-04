import logging
import logging.config
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import nltk
import redis
from dotenv import load_dotenv
from minio import Minio
from sqlmodel import SQLModel, create_engine

from src.common.check_google_api_tokens import check_google_api_tokens

load_dotenv()

ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")

# Múi giờ Việt Nam
VN_TIMEZONE = ZoneInfo("Asia/Ho_Chi_Minh")


def get_now_vn():
    return datetime.now(VN_TIMEZONE).isoformat(timespec="milliseconds")


# Custom formatter cho múi giờ Việt Nam
class VietnamTimeFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created, tz=VN_TIMEZONE)
        return dt.isoformat(timespec="milliseconds")


# --- Các biến config ---
DEBUG = os.getenv("DEBUG", "False") == "True"

POSTGRES_DB = os.getenv("POSTGRES_DB", "backend_database")
POSTGRES_USER = os.getenv("POSTGRES_USER", "admin")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "admin")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
DATABASE_URL = f"postgresql+psycopg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

MINIO_URL = os.getenv("MINIO_URL", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")


EMBEDDING_DIM = 3072

GOOGLE_API_KEYS = None

with open("env/google_api_keys.txt", "r") as f:
    GOOGLE_API_KEYS = [line.strip() for line in f.readlines() if line.strip()]

    if ENVIRONMENT != "dev":
        check_google_api_tokens(GOOGLE_API_KEYS)


def initialize_nltk():
    nltk.download("punkt", quiet=True)
    nltk.download("stopwords", quiet=True)


initialize_nltk()


def get_minio_client():
    logging.info(f"Connecting to MinIO at '{MINIO_URL}'")
    return Minio(
        MINIO_URL,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False,  # True if using HTTPS, False if using HTTP
    )


# --- Hàm khởi tạo ---
def get_engine():
    logging.info(f"Connecting to database at '{DATABASE_URL}'")
    return create_engine(DATABASE_URL)


def create_vector_extension():
    """Create the 'vector' extension in Postgres if it does not exist."""
    from sqlalchemy import text

    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        conn.commit()


create_vector_extension()


# initialize database
def init_db():
    from src import repositories  # noqa: F401

    SQLModel.metadata.create_all(get_engine())


def get_redis_client():
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)


# Runtime data
RUNTIME_DATA_DIR = Path(__file__).parent.parent / "data"
RUNTIME_DATA_DIR.mkdir(exist_ok=True)

# --- Logging ---
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "()": VietnamTimeFormatter,
            "format": "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s",
        },
        "detailed": {
            "()": VietnamTimeFormatter,
            "format": "%(asctime)s | %(levelname)-8s | %(name)-5s | %(module)s.%(funcName)s:%(lineno)d | %(message)s",
        },
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(funcName)s %(lineno)d %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO" if not DEBUG else "DEBUG",
            "formatter": "standard",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "formatter": "detailed",
            "filename": str(LOG_DIR / "app.log"),
            "maxBytes": 10485760,
            "backupCount": 5,
            "encoding": "utf8",
        },
        "error_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "ERROR",
            "formatter": "detailed",
            "filename": str(LOG_DIR / "error.log"),
            "maxBytes": 10485760,
            "backupCount": 5,
            "encoding": "utf8",
        },
    },
    "root": {
        "level": "DEBUG" if DEBUG else "INFO",
        "handlers": ["console", "file"],
    },
    "loggers": {
        "uvicorn": {
            "level": "INFO",
            "handlers": ["console", "file"],
            "propagate": False,
        },
        "uvicorn.access": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False,
        },
        "uvicorn.error": {
            "level": "ERROR",
            "handlers": ["console", "error_file"],
            "propagate": False,
        },
        "redis": {
            "level": "WARNING",
            "handlers": ["console", "file"],
            "propagate": False,
        },
    },
}


def setup_logging():
    logging.config.dictConfig(LOGGING_CONFIG)

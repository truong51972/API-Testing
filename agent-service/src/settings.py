import logging
import logging.config
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import langchain
import nltk
import redis
from dotenv import load_dotenv
from minio import Minio
from sqlmodel import SQLModel, create_engine

load_dotenv()

ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")

# Múi giờ Việt Nam
VN_TIMEZONE = ZoneInfo("Asia/Ho_Chi_Minh")

langchain.debug = True


def get_now_vn():
    now_vn = datetime.now(VN_TIMEZONE)
    return now_vn.replace(tzinfo=None)


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
POSTGRES_URL = f"postgresql+psycopg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

MINIO_URL = os.getenv("MINIO_URL", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", "http://localhost:8000/v1/")
VLLM_API_KEY = os.getenv("VLLM_API_KEY", "NONE")

EMBEDDING_DIM = 3072


def initialize_nltk():
    nltk.download("punkt", quiet=True)
    nltk.download("stopwords", quiet=True)


def get_minio_client(verbose: bool = False):
    if verbose:
        logging.info(f"Connecting to MinIO at '{MINIO_URL}'")
    return Minio(
        MINIO_URL,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False,  # True if using HTTPS, False if using HTTP
    )


# --- Hàm khởi tạo ---
def get_db_engine(verbose: bool = False):
    if verbose:
        logging.info(f"Connecting to database at '{POSTGRES_URL}'")
    return create_engine(POSTGRES_URL)


def create_vector_extension(verbose: bool = False):
    """Create the 'vector' extension in Postgres if it does not exist."""
    from sqlalchemy import text

    if verbose:
        logging.info("Creating 'vector' extension in Postgres if not exists...")

    engine = get_db_engine()
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        conn.commit()


# initialize database
def init_db(verbose: bool = False):
    from src import repositories  # noqa: F401

    if verbose:
        logging.info("Initializing database and creating tables...")
    SQLModel.metadata.create_all(get_db_engine(verbose))


def get_redis_client(verbose: bool = False):
    if verbose:
        logging.info(
            f"Connecting to Redis at '{REDIS_HOST}:{REDIS_PORT}', DB {REDIS_DB}"
        )
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)


# Runtime data
RUNTIME_DATA_DIR = Path(__file__).parent.parent / "data"
RUNTIME_DATA_DIR.mkdir(exist_ok=True)

# --- Logging ---
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
logger = logging.getLogger("app")

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
            "format": f"{'='*60}\nTime: %(asctime)s\nLevel: %(levelname)-8s\nLogger Name: %(name)-5s\nModule: %(module)s.%(funcName)s:%(lineno)d\n{'='*60}\n%(message)s\n\n",
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
        "info_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "formatter": "detailed",
            "filename": str(LOG_DIR / "info.log"),
            "maxBytes": 10485760,
            "backupCount": 5,
            "encoding": "utf8",
        },
        "access_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "formatter": "detailed",
            "filename": str(LOG_DIR / "access.log"),
            "maxBytes": 10485760,
            "backupCount": 5,
            "encoding": "utf8",
        },
        "debug_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG",
            "formatter": "detailed",
            "filename": str(LOG_DIR / "debug.log"),
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
        "level": "DEBUG",
        "handlers": ["console"],
    },
    "loggers": {
        "app": {
            "level": "DEBUG",
            "handlers": ["console", "info_file", "debug_file", "error_file"],
            "propagate": False,
        },
        "uvicorn": {
            "level": "INFO",
            "handlers": ["console", "info_file"],
            "propagate": False,
        },
        "uvicorn.access": {
            "level": "INFO",
            "handlers": ["console", "access_file"],
            "propagate": False,
        },
        "uvicorn.debug": {
            "level": "DEBUG",
            "handlers": ["console", "debug_file"],
            "propagate": False,
        },
        "uvicorn.error": {
            "level": "ERROR",
            "handlers": ["console", "error_file"],
            "propagate": False,
        },
    },
}


def setup_logging():
    logging.config.dictConfig(LOGGING_CONFIG)


def setup(verbose: bool = False):
    setup_logging()
    initialize_nltk()
    create_vector_extension(verbose)
    init_db(verbose)
    get_redis_client(verbose)

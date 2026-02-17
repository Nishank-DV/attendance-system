import os

from dotenv import load_dotenv


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(BASE_DIR, ".env"))


def _get_int_env(key: str, default: int) -> int:
    value = os.getenv(key)
    if value is None or value.strip() == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _get_float_env(key: str, default: float) -> float:
    value = os.getenv(key)
    if value is None or value.strip() == "":
        return default
    try:
        return float(value)
    except ValueError:
        return default


class AppConfig:
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = _get_int_env("PORT", 5000)
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    BASE_DIR = BASE_DIR
    BACKEND_DIR = os.path.join(BASE_DIR, "backend")
    DATA_DIR = os.path.join(BACKEND_DIR, "data")

    FACULTY_DB_PATH = os.path.join(DATA_DIR, "faculty_users.json")

    STUDENTS_DB_PATH = os.path.join(DATA_DIR, "students.json")
    ATTENDANCE_JSON = os.path.join(DATA_DIR, "attendance.json")

    FACE_TOLERANCE = _get_float_env("FACE_TOLERANCE", 0.6)
    COOLDOWN_SECONDS = _get_int_env("COOLDOWN_SECONDS", 120)
    ESP32_BASE_URL = os.getenv("ESP32_BASE_URL", "http://192.168.4.1")

    FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "smartvision-dev-secret")
    FACULTY_USERNAME = os.getenv("FACULTY_USERNAME", "faculty")
    FACULTY_PASSWORD = os.getenv("FACULTY_PASSWORD", "faculty123")
    FACULTY_RESET_KEY = os.getenv("FACULTY_RESET_KEY", "reset123")
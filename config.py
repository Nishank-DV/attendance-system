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


def _get_bool_env(key: str, default: bool) -> bool:
    value = os.getenv(key)
    if value is None or value.strip() == "":
        return default

    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _get_str_env(key: str, default: str) -> str:
    value = os.getenv(key)
    if value is None:
        return default

    normalized = value.strip()
    return normalized if normalized else default


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
    FACE_DETECTION_MODEL = _get_str_env("FACE_DETECTION_MODEL", "hog").lower()
    FACE_ENCODING_MODEL = _get_str_env("FACE_ENCODING_MODEL", "small").lower()
    FACE_FRAME_RESIZE_SCALE = _get_float_env("FACE_FRAME_RESIZE_SCALE", 1.0)
    FACE_USE_GRAYSCALE = _get_bool_env("FACE_USE_GRAYSCALE", False)
    RECOGNITION_FRAME_SKIP = max(1, _get_int_env("RECOGNITION_FRAME_SKIP", 2))
    ESP32_DISCONNECT_TIMEOUT_SECONDS = _get_int_env("ESP32_DISCONNECT_TIMEOUT_SECONDS", 6)
    COOLDOWN_SECONDS = _get_int_env("COOLDOWN_SECONDS", 120)
    ESP32_BASE_URL = _get_str_env("ESP32_BASE_URL", "http://192.168.4.1")

    FLASK_SECRET_KEY = _get_str_env("FLASK_SECRET_KEY", "smartvision-dev-secret")
    FACULTY_USERNAME = _get_str_env("FACULTY_USERNAME", "faculty")
    FACULTY_PASSWORD = _get_str_env("FACULTY_PASSWORD", "faculty123")
    FACULTY_RESET_KEY = _get_str_env("FACULTY_RESET_KEY", "reset123")
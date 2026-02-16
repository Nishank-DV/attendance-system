import os


class AppConfig:
    HOST = "0.0.0.0"
    PORT = 5000
    LOG_LEVEL = "INFO"

    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    KNOWN_FACES_DIR = os.path.join(BASE_DIR, "known_faces")

    ATTENDANCE_CSV = os.path.join(
        BASE_DIR, "attendance_records", "attendance.csv"
    )

    FACE_TOLERANCE = 0.6

    COOLDOWN_SECONDS = 120

    ESP32_BASE_URL = "http://192.168.4.1"
import base64
import binascii
import logging
from threading import Lock
from typing import Any, Dict, Optional

from flask import Flask, Request, jsonify, redirect, request, session, url_for
from flask_cors import CORS

from attendance_service import AttendanceService
from config import AppConfig
from faculty_db import FacultyDB
from recognition_service import build_default_recognition_service
from registration import create_registration_blueprint
from routes.auth import create_auth_blueprint
from routes.dashboard import create_dashboard_blueprint
from student_db import StudentDB
from utils import configure_logging

# Thread-safe device mode for ESP32 polling/control.
current_mode = "idle"
mode_lock = Lock()
ALLOWED_MODES = {"idle", "register", "attendance"}


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = AppConfig.FLASK_SECRET_KEY
    app.url_map.strict_slashes = False

    CORS(app, supports_credentials=True)
    configure_logging(AppConfig.LOG_LEVEL)

    student_db = StudentDB(AppConfig.STUDENTS_DB_PATH)
    faculty_db = FacultyDB(AppConfig.FACULTY_DB_PATH)
    faculty_db.ensure_default_user(AppConfig.FACULTY_USERNAME, AppConfig.FACULTY_PASSWORD)
    recognition_service = build_default_recognition_service(student_db)
    attendance_service = AttendanceService(
        json_path=AppConfig.ATTENDANCE_JSON,
        cooldown_seconds=AppConfig.COOLDOWN_SECONDS,
    )

    app.register_blueprint(
        create_registration_blueprint(
            student_db=student_db,
            recognition_service=recognition_service,
            faculty_db=faculty_db,
        )
    )
    app.register_blueprint(
        create_auth_blueprint(
            faculty_db=faculty_db,
            reset_key=AppConfig.FACULTY_RESET_KEY,
        )
    )
    app.register_blueprint(create_dashboard_blueprint())

    logging.info("=" * 50)
    logging.info("SmartVision Attendance Backend is Running ✅")
    logging.info("=" * 50)

    @app.get("/")
    def home():
        if session.get("faculty_logged_in"):
            return redirect(url_for("dashboard.attendance_page"))
        return redirect(url_for("auth.faculty_page"))

    @app.get("/health")
    def health_check():
        with mode_lock:
            mode = current_mode
        return (
            jsonify(
                {
                    "status": "ok",
                    "service": "smartvision-backend",
                    "mode": mode,
                }
            ),
            200,
        )

    @app.get("/device_mode")
    def device_mode():
        with mode_lock:
            mode = current_mode
        return jsonify({"status": "ok", "mode": mode}), 200

    @app.get("/set_mode/<mode>")
    def set_mode(mode: str):
        normalized_mode = str(mode or "").strip().lower()
        if normalized_mode not in ALLOWED_MODES:
            return _json_error(
                400,
                "invalid_mode",
                "Invalid mode. Allowed values: idle, register, attendance.",
            )

        with mode_lock:
            global current_mode
            current_mode = normalized_mode

        return jsonify({"status": "ok", "mode": normalized_mode}), 200

    @app.get("/api/attendance")
    def get_attendance():
        target_date = request.args.get("date")
        try:
            records = attendance_service.get_records(target_date)
            selected_date = target_date or attendance_service.get_active_date()
            return jsonify({"status": "ok", "date": selected_date, "records": records}), 200
        except ValueError as exc:
            return _json_error(400, "invalid_date", str(exc))
        except Exception as exc:
            logging.exception("Failed to fetch attendance")
            return _json_error(500, "attendance_error", str(exc))

    @app.post("/api/set-date")
    def set_attendance_date():
        payload = request.get_json(silent=True) or {}
        target_date = str(payload.get("date", "")).strip()
        if not target_date:
            return _json_error(400, "missing_date", "date is required.")

        try:
            selected = attendance_service.set_active_date(target_date)
            return jsonify({"status": "ok", "date": selected}), 200
        except ValueError as exc:
            return _json_error(400, "invalid_date", str(exc))
        except Exception as exc:
            logging.exception("Failed to set attendance date")
            return _json_error(500, "attendance_error", str(exc))

    @app.get("/api/summary")
    def get_summary():
        target_date = request.args.get("date")
        try:
            summary = attendance_service.get_summary(target_date)
            summary["status"] = "ok"
            return jsonify(summary), 200
        except ValueError as exc:
            return _json_error(400, "invalid_date", str(exc))
        except Exception as exc:
            logging.exception("Failed to load summary")
            return _json_error(500, "summary_error", str(exc))

    @app.post("/api/trigger-buzzer")
    def trigger_buzzer():
        payload = request.get_json(silent=True) or {}
        pattern = str(payload.get("pattern", "")).strip()

        if not pattern:
            return _json_error(400, "missing_pattern", "pattern is required.")

        ok, message = attendance_service.trigger_buzzer(pattern)
        if ok:
            return jsonify({"status": "ok", "message": message}), 200
        return _json_error(502, "esp32_unreachable", message)

    @app.post("/api/recognize")
    @app.post("/recognize")
    @app.post("/upload")
    def recognize_face():
        try:
            image_bytes = _extract_image_bytes_from_request(request)
            if image_bytes is None:
                return _json_error(
                    400,
                    "invalid_payload",
                    "Provide image_base64 in JSON body or a valid image upload.",
                )

            result = recognition_service.recognize(image_bytes)
            result_status = str(result.get("status", "error"))

            if result_status == "no_face":
                return jsonify({"status": "no_face", "recognized": False}), 200

            if result_status == "unknown":
                attendance_service.mark_unknown()
                return jsonify({"status": "unknown", "recognized": False}), 200

            if result_status == "error":
                return _json_error(500, "recognition_error", str(result.get("message", "Recognition failed.")))

            student = student_db.get_student_by_id(int(result["student_id"]))
            if student is None:
                attendance_service.mark_unknown()
                return jsonify(
                    {
                        "status": "unknown",
                        "recognized": False,
                        "message": "Matched profile no longer exists.",
                    }
                ), 200

            target_date = request.args.get("date") or request.form.get("date") or None
            attendance_result = attendance_service.mark_attendance(
                student=student,
                confidence=float(result.get("confidence", 0.0)),
                target_date=target_date,
            )

            with mode_lock:
                mode = current_mode

            return (
                jsonify(
                    {
                        "status": "present",
                        "recognized": True,
                        "mode": mode,
                        "name": student["name"],
                        "roll_number": student.get("roll_number", ""),
                        "department": student.get("department", ""),
                        "attendance_status": attendance_result.get("status", "entry"),
                        "confidence": round(float(result.get("confidence", 0.0)), 2),
                        "date": attendance_result.get("date"),
                        "timestamp": attendance_result.get("timestamp", ""),
                    }
                ),
                200,
            )

        except ValueError as exc:
            return _json_error(400, "invalid_data", str(exc))
        except Exception as exc:
            logging.exception("Recognition failed")
            return _json_error(500, "server_error", str(exc))

    @app.errorhandler(404)
    def not_found(_error):
        return _json_error(404, "not_found", "Route not found.")

    @app.errorhandler(405)
    def method_not_allowed(_error):
        return _json_error(405, "method_not_allowed", "HTTP method not allowed for this route.")

    @app.errorhandler(500)
    def internal_error(_error):
        return _json_error(500, "server_error", "Internal server error.")

    return app


def _extract_image_bytes_from_request(req: Request) -> Optional[bytes]:
    # Preferred path: JSON base64 payload from ESP32.
    payload = req.get_json(silent=True)
    if isinstance(payload, dict):
        encoded = payload.get("image_base64")
        if isinstance(encoded, str) and encoded.strip():
            if "," in encoded:
                encoded = encoded.split(",", 1)[1]
            try:
                decoded = base64.b64decode(encoded, validate=True)
                return decoded if decoded else None
            except (ValueError, binascii.Error):
                return None

    # Backward compatibility: multipart/form-data image upload.
    if req.files:
        file = req.files.get("image") or next(iter(req.files.values()), None)
        if file is not None:
            raw = file.read()
            return raw if raw else None

    # Optional fallback: raw image bytes.
    if (req.content_type or "").startswith("image/") or req.mimetype == "application/octet-stream":
        raw = req.get_data(cache=False)
        return raw if raw else None

    return None


def _json_error(http_code: int, code: str, message: str):
    return (
        jsonify(
            {
                "status": "error",
                "error": {
                    "code": code,
                    "message": message,
                },
            }
        ),
        http_code,
    )


if __name__ == "__main__":
    app = create_app()
    app.run(host=AppConfig.HOST, port=AppConfig.PORT, debug=False)

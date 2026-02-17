import base64
import logging
from typing import Optional

from flask import Flask, Request, jsonify, redirect, request, session, url_for
from flask_cors import CORS

from config import AppConfig
from attendance_service import AttendanceService
from faculty_db import FacultyDB
from recognition_service import build_default_recognition_service
from registration import create_registration_blueprint
from routes.auth import create_auth_blueprint
from routes.dashboard import create_dashboard_blueprint
from student_db import StudentDB
from utils import configure_logging


def create_app() -> Flask:
    """Initialize Flask app and load dependencies."""
    app = Flask(__name__)
    app.secret_key = AppConfig.FLASK_SECRET_KEY
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

    @app.get("/api/attendance")
    def get_attendance():
        """Return attendance records for selected date or provided date."""
        target_date = request.args.get("date")
        try:
            records = attendance_service.get_records(target_date)
            selected_date = target_date or attendance_service.get_active_date()
        except ValueError as exc:
            return jsonify({"status": "error", "message": str(exc)}), 400

        return jsonify({"date": selected_date, "records": records})

    @app.post("/api/set-date")
    def set_attendance_date():
        payload = request.get_json(silent=True) or {}
        target_date = payload.get("date")
        if not target_date:
            return jsonify({"status": "error", "message": "date is required."}), 400

        try:
            selected = attendance_service.set_active_date(str(target_date))
        except ValueError as exc:
            return jsonify({"status": "error", "message": str(exc)}), 400

        return jsonify({"status": "ok", "date": selected})

    @app.get("/api/summary")
    def get_summary():
        target_date = request.args.get("date")
        try:
            summary = attendance_service.get_summary(target_date)
        except ValueError as exc:
            return jsonify({"status": "error", "message": str(exc)}), 400

        return jsonify(summary)

    @app.post("/api/recognize")
    def recognize():
        """Recognize face from request image and update attendance state."""
        try:
            image_bytes = _extract_image_bytes_from_request(request)
            if image_bytes is None:
                return jsonify({"status": "error", "message": "No image provided."}), 400

            result = recognition_service.recognize(image_bytes)

            if result["status"] == "no_face":
                return jsonify(result), 200

            if result["status"] == "unknown":
                attendance_service.mark_unknown()
                return jsonify(result), 200

            if result["status"] == "error":
                return jsonify(result), 500

            student = student_db.get_student_by_id(result["student_id"])
            if student is None:
                attendance_service.mark_unknown()
                return jsonify({"status": "unregistered", "message": "Matched profile no longer exists."}), 200

            attendance_result = attendance_service.mark_attendance(
                student=student,
                confidence=result["confidence"],
            )

            return jsonify(attendance_result), 200

        except Exception as exc:
            logging.exception("Recognition failed")
            return jsonify({"status": "error", "message": str(exc)}), 500

    @app.post("/api/trigger-buzzer")
    def trigger_buzzer():
        payload = request.get_json(silent=True) or {}
        pattern = payload.get("pattern")

        if not pattern:
            return jsonify({"status": "error", "message": "pattern is required."}), 400

        ok, message = attendance_service.trigger_buzzer(pattern)
        status = "ok" if ok else "error"
        code = 200 if ok else 502

        return jsonify({"status": status, "message": message}), code

    return app


def _extract_image_bytes_from_request(req: Request) -> Optional[bytes]:
    """Extract raw image bytes from request (multipart or base64 JSON)."""
    try:
        if "image" in req.files:
            file = req.files["image"]
            if file.filename == "":
                logging.warning("Empty filename in image upload")
                return None
            return file.read()

        payload = req.get_json(silent=True) or {}
        if "image_base64" not in payload:
            logging.warning("No image or image_base64 found in request")
            return None

        encoded = payload["image_base64"]
        if "," in encoded:
            encoded = encoded.split(",", 1)[1]
        return base64.b64decode(encoded)
    except Exception as exc:
        logging.error("Error extracting image from request: %s", exc)
        return None


if __name__ == "__main__":
    app = create_app()
    app.run(host=AppConfig.HOST, port=AppConfig.PORT, debug=False)
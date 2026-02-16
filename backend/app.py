import base64
import logging
from datetime import datetime

from flask import Flask, jsonify, request
from flask_cors import CORS

from config import AppConfig
from attendance import AttendanceService
from recognition import FaceRecognition
from database import AttendanceStore
from utils import configure_logging


def create_app() -> Flask:
    """Initialize Flask app and load dependencies."""
    app = Flask(__name__)
    CORS(app)
    configure_logging(AppConfig.LOG_LEVEL)

    # Initialize storage
    store = AttendanceStore()

    # Load known faces at startup (initializes ONCE)
    face_recognition_engine = FaceRecognition(known_faces_dir=AppConfig.KNOWN_FACES_DIR)

    # Initialize attendance service (initializes ONCE)
    attendance_service = AttendanceService(
        store=store,
        cooldown_seconds=AppConfig.COOLDOWN_SECONDS,
    )

    logging.info("="*50)
    logging.info("SmartVision Attendance Backend is Running ✅")
    logging.info("="*50)

    @app.get("/")
    def home():
        return "SmartVision Attendance Backend is Running ✅"

    @app.get("/api/attendance")
    def get_attendance():
        """Return all attendance records."""
        records = store.read_records()
        return jsonify({"records": records})

    @app.get("/api/summary")
    def get_summary():
        summary = store.get_daily_summary(datetime.utcnow().date())
        return jsonify(summary)

    @app.post("/api/recognize")
    def recognize():
        """
        Handle face recognition and mark attendance.
        Accepts image file and returns JSON response.
        """
        try:
            # Extract image bytes from request (accepts image file)
            image_bytes = _extract_image_bytes_from_request(request)
            if image_bytes is None:
                return jsonify({"status": "error", "message": "No image provided."}), 400

            # Pass image bytes to recognition module
            result = face_recognition_engine.recognize_face(image_bytes)

            # Handle no face detected
            if result["status"] == "no_face":
                return jsonify(result), 200

            # Handle unknown face
            if result["status"] == "unknown":
                return jsonify(result), 200

            # Handle recognition error
            if result["status"] == "error":
                return jsonify(result), 500

            # If recognized: call attendance.mark_attendance()
            attendance_result = attendance_service.mark_attendance(
                name=result["name"],
                confidence=result["confidence"],
            )
            
            # Return final JSON response
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


def _extract_image_bytes_from_request(req: request):
    """Extract raw image bytes from request (multipart or base64 JSON)."""
    try:
        # Check for multipart file upload
        if "image" in req.files:
            file = req.files["image"]
            if file.filename == "":
                logging.warning("Empty filename in image upload")
                return None
            return file.read()

        # Check for base64 JSON payload
        payload = req.get_json(silent=True) or {}
        if "image_base64" not in payload:
            logging.warning("No image or image_base64 found in request")
            return None

        encoded = payload["image_base64"]
        if "," in encoded:
            encoded = encoded.split(",", 1)[1]
        return base64.b64decode(encoded)
    except Exception as e:
        logging.error(f"Error extracting image from request: {e}")
        return None


if __name__ == "__main__":
    app = create_app()
    app.run(host=AppConfig.HOST, port=AppConfig.PORT, debug=False)
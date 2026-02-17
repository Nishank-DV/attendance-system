import base64
from functools import wraps
from typing import Callable, Optional, Tuple

import cv2
import face_recognition
import numpy as np
from flask import Blueprint, jsonify, request, session

from faculty_db import FacultyDB
from student_db import StudentDB
from recognition_service import RecognitionService


def _login_required(handler: Callable):
    @wraps(handler)
    def wrapper(*args, **kwargs):
        if not session.get("faculty_logged_in"):
            return jsonify({"status": "error", "message": "Unauthorized"}), 401
        return handler(*args, **kwargs)

    return wrapper


def create_registration_blueprint(
    student_db: StudentDB,
    recognition_service: RecognitionService,
    faculty_db: FacultyDB,
) -> Blueprint:
    bp = Blueprint("registration", __name__)

    @bp.post("/api/faculty/login")
    def faculty_login():
        payload = request.get_json(silent=True) or {}
        username = str(payload.get("username", "")).strip()
        password = str(payload.get("password", "")).strip()

        if not faculty_db.verify_user(username, password):
            return jsonify({"status": "error", "message": "Invalid credentials."}), 401

        session["faculty_logged_in"] = True
        session["faculty_username"] = username
        user = faculty_db.get_user(username)
        session["faculty_is_admin"] = bool(user.get("is_admin")) if user else False
        return jsonify({"status": "ok", "username": username})

    @bp.post("/api/faculty/logout")
    def faculty_logout():
        session.clear()
        return jsonify({"status": "ok"})

    @bp.get("/api/faculty/session")
    def faculty_session():
        if session.get("faculty_logged_in"):
            return jsonify({"logged_in": True, "username": session.get("faculty_username")})
        return jsonify({"logged_in": False})

    @bp.post("/api/register-student")
    @_login_required
    def register_student():
        payload = request.get_json(silent=True) or {}

        name = str(payload.get("name", "")).strip()
        roll_number = str(payload.get("roll_number", "")).strip()
        department = str(payload.get("department", "")).strip()

        if not name or not roll_number or not department:
            return jsonify({"status": "error", "message": "name, roll_number, department are required."}), 400

        image_base64 = payload.get("image_base64")
        image_file = request.files.get("image") if request.files else None

        if not image_base64 and image_file is None:
            return jsonify({"status": "error", "message": "image_base64 or image is required."}), 400

        if image_base64:
            rgb_image = _decode_base64_image(image_base64)
        else:
            rgb_image = _decode_bytes_image(image_file.read())

        if rgb_image is None:
            return jsonify({"status": "error", "message": "Invalid image data."}), 400

        encoding, status = _extract_single_face_encoding(rgb_image)
        if status == "no_face":
            return jsonify({"status": "no_face", "message": "No face detected in registration image."}), 200
        if status == "multiple_faces":
            return jsonify({"status": "error", "message": "Multiple faces detected. Use a single face."}), 400

        try:
            student = student_db.register_student(
                name=name,
                roll_number=roll_number,
                department=department,
                encoding=encoding.tolist(),
            )
        except ValueError as exc:
            return jsonify({"status": "error", "message": str(exc)}), 409

        return jsonify(
            {
                "status": "registered",
                "student": {
                    "id": student["id"],
                    "name": student["name"],
                    "roll_number": student["roll_number"],
                    "department": student["department"],
                },
            }
        )

    @bp.get("/api/students")
    @_login_required
    def get_students():
        students = student_db.get_students(include_encoding=False)
        return jsonify({"students": students})

    @bp.post("/api/delete-student")
    @_login_required
    def delete_student():
        payload = request.get_json(silent=True) or {}
        student_id = payload.get("id")
        if student_id is None:
            return jsonify({"status": "error", "message": "id is required."}), 400

        deleted = student_db.delete_student(int(student_id))
        if not deleted:
            return jsonify({"status": "error", "message": "Student not found."}), 404

        return jsonify({"status": "ok"})

    return bp


def _decode_base64_image(image_base64: str) -> Optional[np.ndarray]:
    try:
        encoded = image_base64
        if "," in encoded:
            encoded = encoded.split(",", 1)[1]
        image_bytes = base64.b64decode(encoded)
        return _decode_bytes_image(image_bytes)
    except Exception:
        return None


def _decode_bytes_image(image_bytes: bytes) -> Optional[np.ndarray]:
    try:
        image_array = np.frombuffer(image_bytes, dtype=np.uint8)
        bgr_image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        if bgr_image is None:
            return None
        return cv2.cvtColor(bgr_image, cv2.COLOR_BGR2RGB)
    except Exception:
        return None


def _extract_single_face_encoding(rgb_image: np.ndarray) -> Tuple[Optional[np.ndarray], str]:
    face_locations = face_recognition.face_locations(rgb_image)
    if len(face_locations) == 0:
        return None, "no_face"
    if len(face_locations) > 1:
        return None, "multiple_faces"

    encodings = face_recognition.face_encodings(rgb_image, known_face_locations=face_locations)
    if not encodings:
        return None, "no_face"
    return encodings[0], "ok"

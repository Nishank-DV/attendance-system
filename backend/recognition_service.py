import io
import logging
from typing import Dict, Optional

import face_recognition
import numpy as np
from PIL import Image, ImageOps

from config import AppConfig
from student_db import StudentDB


class RecognitionService:
    def __init__(self, student_db: StudentDB, tolerance: float) -> None:
        self.student_db = student_db
        self.tolerance = tolerance

    def extract_encoding(self, image_bytes: bytes) -> Optional[np.ndarray]:
        image = Image.open(io.BytesIO(image_bytes))
        image = ImageOps.exif_transpose(image)
        image_array = np.array(image)

        if image_array.ndim == 2:
            image_array = np.stack([image_array] * 3, axis=-1)
        elif image_array.ndim == 3 and image_array.shape[2] == 4:
            image_array = image_array[:, :, :3]

        encodings = face_recognition.face_encodings(image_array)
        if not encodings:
            return None

        return encodings[0]

    def recognize(self, image_bytes: bytes) -> Dict:
        try:
            probe_encoding = self.extract_encoding(image_bytes)
            if probe_encoding is None:
                return {"status": "no_face"}

            students = self.student_db.get_students(include_encoding=True)
            if not students:
                return {"status": "unknown", "message": "No registered students."}

            known_encodings = []
            known_students = []
            for student in students:
                vector = student.get("encoding")
                if isinstance(vector, list) and vector:
                    known_encodings.append(np.array(vector, dtype=np.float64))
                    known_students.append(student)

            if not known_encodings:
                return {"status": "unknown", "message": "No valid student encodings."}

            distances = face_recognition.face_distance(known_encodings, probe_encoding)
            best_index = int(np.argmin(distances))
            best_distance = float(distances[best_index])

            if best_distance > self.tolerance:
                return {"status": "unknown"}

            confidence = round((1 - best_distance) * 100, 2)
            student = known_students[best_index]

            return {
                "status": "recognized",
                "student_id": student["id"],
                "name": student["name"],
                "roll_number": student["roll_number"],
                "department": student["department"],
                "confidence": confidence,
                "distance": round(best_distance, 5),
            }

        except Exception as exc:
            logging.exception("Recognition failure")
            return {"status": "error", "message": str(exc)}


def build_default_recognition_service(student_db: StudentDB) -> RecognitionService:
    return RecognitionService(student_db=student_db, tolerance=AppConfig.FACE_TOLERANCE)

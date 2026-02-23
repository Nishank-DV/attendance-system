import io
import logging
import threading
from typing import Dict, List, Optional, Tuple

import cv2
import face_recognition
import numpy as np
from PIL import Image, ImageOps

from config import AppConfig
from student_db import StudentDB


class RecognitionService:
    def __init__(
        self,
        student_db: StudentDB,
        tolerance: float,
        detection_model: str,
        encoding_model: str,
        resize_scale: float,
        use_grayscale: bool,
    ) -> None:
        self.student_db = student_db
        self.tolerance = tolerance
        self.detection_model = detection_model if detection_model in {"hog", "cnn"} else "hog"
        self.encoding_model = encoding_model if encoding_model in {"small", "large"} else "small"
        self.resize_scale = max(0.1, min(float(resize_scale), 1.0))
        self.use_grayscale = bool(use_grayscale)
        self._cache_lock = threading.Lock()
        self._known_encodings: List[np.ndarray] = []
        self._known_students: List[Dict] = []
        self.reload_known_faces()

    @staticmethod
    def _is_valid_encoding(value) -> bool:
        if not isinstance(value, list) or len(value) != 128:
            return False

        try:
            vector = np.array(value, dtype=np.float64)
            return bool(np.isfinite(vector).all())
        except Exception:
            return False

    def reload_known_faces(self) -> int:
        students = self.student_db.get_students(include_encoding=True)
        valid_encodings: List[np.ndarray] = []
        valid_students: List[Dict] = []

        for student in students:
            vector = student.get("encoding")
            if not self._is_valid_encoding(vector):
                logging.warning("Skipping invalid encoding for student id=%s", student.get("id"))
                continue

            valid_encodings.append(np.array(vector, dtype=np.float64))
            valid_students.append(student)

        with self._cache_lock:
            self._known_encodings = valid_encodings
            self._known_students = valid_students

        logging.info("Loaded %d valid face encodings", len(valid_encodings))
        return len(valid_encodings)

    def _decode_and_prepare(self, image_bytes: bytes) -> np.ndarray:
        image = Image.open(io.BytesIO(image_bytes))
        image = ImageOps.exif_transpose(image)
        image_array = np.array(image)

        if image_array.ndim == 2:
            image_array = np.stack([image_array] * 3, axis=-1)
        elif image_array.ndim == 3 and image_array.shape[2] == 4:
            image_array = image_array[:, :, :3]

        if self.use_grayscale:
            gray = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)
            image_array = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)

        if self.resize_scale < 1.0:
            image_array = cv2.resize(
                image_array,
                dsize=None,
                fx=self.resize_scale,
                fy=self.resize_scale,
                interpolation=cv2.INTER_LINEAR,
            )

        return image_array

    def extract_face_data(self, image_bytes: bytes) -> Tuple[Optional[np.ndarray], str]:
        image_array = self._decode_and_prepare(image_bytes)
        face_locations = face_recognition.face_locations(image_array, model=self.detection_model)

        if len(face_locations) == 0:
            return None, "no_face"
        if len(face_locations) > 1:
            return None, "multiple_faces"

        encodings = face_recognition.face_encodings(
            image_array,
            known_face_locations=face_locations,
            model=self.encoding_model,
        )
        if not encodings:
            return None, "no_face"

        return encodings[0], "ok"

    def extract_encoding(self, image_bytes: bytes) -> Optional[np.ndarray]:
        encoding, status = self.extract_face_data(image_bytes)
        if status != "ok":
            return None
        return encoding

    def recognize(self, image_bytes: bytes) -> Dict:
        try:
            probe_encoding, status = self.extract_face_data(image_bytes)
            if status != "ok":
                return {"status": status}

            with self._cache_lock:
                known_encodings = list(self._known_encodings)
                known_students = list(self._known_students)

            if not known_encodings:
                return {"status": "unknown", "message": "No registered students."}

            distances = face_recognition.face_distance(known_encodings, probe_encoding)
            best_index = int(np.argmin(distances))
            best_distance = float(distances[best_index])
            logging.info("Recognition best distance=%.5f threshold=%.3f", best_distance, self.tolerance)

            if best_distance > self.tolerance:
                return {
                    "status": "unknown",
                    "distance": round(best_distance, 5),
                    "threshold": self.tolerance,
                }

            ratio = max(0.0, min(1.0, (self.tolerance - best_distance) / self.tolerance))
            confidence = round(ratio * 100, 2)
            student = known_students[best_index]

            return {
                "status": "recognized",
                "student_id": student["id"],
                "name": student["name"],
                "roll_number": student["roll_number"],
                "department": student["department"],
                "confidence": confidence,
                "distance": round(best_distance, 5),
                "threshold": self.tolerance,
            }

        except Exception as exc:
            logging.exception("Recognition failure")
            return {"status": "error", "message": str(exc)}


def build_default_recognition_service(student_db: StudentDB) -> RecognitionService:
    return RecognitionService(
        student_db=student_db,
        tolerance=AppConfig.FACE_TOLERANCE,
        detection_model=AppConfig.FACE_DETECTION_MODEL,
        encoding_model=AppConfig.FACE_ENCODING_MODEL,
        resize_scale=AppConfig.FACE_FRAME_RESIZE_SCALE,
        use_grayscale=AppConfig.FACE_USE_GRAYSCALE,
    )

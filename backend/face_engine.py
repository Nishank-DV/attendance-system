import os
from typing import List, Optional

import face_recognition


class FaceEngine:
    def __init__(self, known_faces_dir: str, tolerance: float, model: str) -> None:
        self.known_faces_dir = known_faces_dir
        self.tolerance = tolerance
        self.model = model
        self.known_encodings = []
        self.known_names = []
        self._load_known_faces()

    def _load_known_faces(self) -> None:
        if not os.path.exists(self.known_faces_dir):
            return

        for root, _, files in os.walk(self.known_faces_dir):
            for filename in files:
                if not filename.lower().endswith((".jpg", ".jpeg", ".png")):
                    continue
                path = os.path.join(root, filename)
                label = self._resolve_label(root, filename)
                image = face_recognition.load_image_file(path)
                encodings = face_recognition.face_encodings(image, model=self.model)
                if encodings:
                    self.known_encodings.append(encodings[0])
                    self.known_names.append(label)

    def match_best(self, face_encodings: List) -> Optional[dict]:
        if not self.known_encodings:
            return None

        best_match = None
        for encoding in face_encodings:
            distances = face_recognition.face_distance(self.known_encodings, encoding)
            if len(distances) == 0:
                continue
            best_index = int(distances.argmin())
            best_distance = distances[best_index]
            if best_distance <= self.tolerance:
                confidence = self._distance_to_confidence(best_distance)
                candidate = {
                    "name": self.known_names[best_index],
                    "confidence": confidence,
                    "distance": float(best_distance),
                }
                if best_match is None or candidate["confidence"] > best_match["confidence"]:
                    best_match = candidate
        return best_match

    @staticmethod
    def _distance_to_confidence(distance: float, max_distance: float = 0.6) -> float:
        if distance >= max_distance:
            return 0.0
        return round((1 - (distance / max_distance)) * 100, 2)

    def _resolve_label(self, root: str, filename: str) -> str:
        rel = os.path.relpath(root, self.known_faces_dir)
        if rel == ".":
            return os.path.splitext(filename)[0]
        return rel.split(os.sep)[0]
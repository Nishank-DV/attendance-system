"""Face recognition module for SmartVision Attendance System."""
import os
import io
import logging
from typing import Dict

import face_recognition
import numpy as np
from PIL import Image


class FaceRecognition:
    """Handles face recognition using face_recognition library."""

    def __init__(self, known_faces_dir: str = None) -> None:
        """
        Initialize face recognition engine.
        
        Args:
            known_faces_dir: Path to known faces directory. 
                           If None, uses project_root/known_faces
        """
        if known_faces_dir is None:
            # Use absolute safe path
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            known_faces_dir = os.path.join(base_dir, "known_faces")
        
        self.known_faces_dir = known_faces_dir
        self.known_encodings = []
        self.known_names = []
        
        # Load known faces at initialization
        self._load_known_faces()

    def _load_known_faces(self) -> None:
        """Load all face encodings from known_faces directory."""
        logging.info("Loading known faces...")
        
        if not os.path.exists(self.known_faces_dir):
            logging.warning(f"Known faces directory not found: {self.known_faces_dir}")
            logging.info("Loaded 0 known faces")
            return

        face_count = 0

        for person_name in os.listdir(self.known_faces_dir):
            person_dir = os.path.join(self.known_faces_dir, person_name)
            
            if not os.path.isdir(person_dir):
                continue

            for filename in os.listdir(person_dir):
                if not filename.lower().endswith((".jpg", ".jpeg", ".png")):
                    continue

                image_path = os.path.join(person_dir, filename)

                try:
                    image = face_recognition.load_image_file(image_path)
                    encodings = face_recognition.face_encodings(image)

                    if encodings:
                        self.known_encodings.append(encodings[0])
                        self.known_names.append(person_name)
                        face_count += 1

                except Exception as e:
                    logging.warning(f"Failed to load {image_path}: {e}")
                    continue

        logging.info(f"Loaded {face_count} known faces")

    def recognize_face(self, image_bytes: bytes) -> Dict:
        """
        Recognize face from image bytes.
        
        Args:
            image_bytes: Raw image bytes
            
        Returns:
            dict: Recognition result with status, name, and confidence
        """
        try:
            # Decode image using PIL and face_recognition
            image = Image.open(io.BytesIO(image_bytes))
            image_array = np.array(image)
            
            # Convert to RGB if needed
            if image_array.ndim == 2:
                image_array = np.stack([image_array] * 3, axis=-1)
            elif image_array.shape[2] == 4:
                image_array = image_array[:, :, :3]
            
            # Detect faces in the image
            face_encodings = face_recognition.face_encodings(image_array)
            
            # If no face detected
            if not face_encodings:
                return {"status": "no_face"}
            
            # If no known faces loaded
            if not self.known_encodings:
                return {"status": "unknown"}
            
            # Compute face distances for first detected face
            face_encoding = face_encodings[0]
            distances = face_recognition.face_distance(self.known_encodings, face_encoding)
            
            # Find best match
            best_index = int(np.argmin(distances))
            best_distance = float(distances[best_index])
            
            # Check if best distance is below threshold
            if best_distance < 0.6:
                confidence = round((1 - best_distance) * 100, 2)
                return {
                    "status": "recognized",
                    "name": self.known_names[best_index],
                    "confidence": confidence
                }
            else:
                return {"status": "unknown"}
                
        except Exception as e:
            logging.error(f"Recognition error: {e}")
            return {"status": "error", "message": str(e)}

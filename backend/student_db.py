import json
import os
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional


class StudentDB:
    def __init__(self, json_path: str) -> None:
        self.json_path = json_path
        self._lock = threading.Lock()
        self._ensure_file()

    def _ensure_file(self) -> None:
        os.makedirs(os.path.dirname(self.json_path), exist_ok=True)
        if not os.path.exists(self.json_path):
            with self._lock:
                with open(self.json_path, "w", encoding="utf-8") as file:
                    json.dump({"next_id": 1, "students": []}, file, indent=2)

    def register_student(
        self,
        name: str,
        roll_number: str,
        department: str,
        encoding: List[float],
    ) -> Dict:
        with self._lock:
            payload = self._read_unsafe()
            students = payload.get("students", [])

            for student in students:
                if student["roll_number"].lower() == roll_number.lower():
                    raise ValueError("Student with this roll number already exists.")

            student_id = int(payload.get("next_id", 1))
            now_iso = datetime.now(timezone.utc).isoformat()

            student = {
                "id": student_id,
                "name": name.strip(),
                "roll_number": roll_number.strip(),
                "department": department.strip(),
                "encoding": [float(value) for value in encoding],
                "created_at": now_iso,
                "updated_at": now_iso,
            }

            students.append(student)
            payload["students"] = students
            payload["next_id"] = student_id + 1
            self._write_unsafe(payload)
            return student

    def get_students(self, include_encoding: bool = False) -> List[Dict]:
        with self._lock:
            payload = self._read_unsafe()

        students = payload.get("students", [])
        if include_encoding:
            return students

        sanitized: List[Dict] = []
        for student in students:
            sanitized.append(
                {
                    "id": student["id"],
                    "name": student["name"],
                    "roll_number": student["roll_number"],
                    "department": student["department"],
                    "created_at": student.get("created_at", ""),
                    "updated_at": student.get("updated_at", ""),
                }
            )
        return sanitized

    def delete_student(self, student_id: int) -> bool:
        with self._lock:
            payload = self._read_unsafe()
            students = payload.get("students", [])
            remaining = [student for student in students if int(student["id"]) != int(student_id)]

            if len(remaining) == len(students):
                return False

            payload["students"] = remaining
            self._write_unsafe(payload)
            return True

    def get_student_by_id(self, student_id: int) -> Optional[Dict]:
        with self._lock:
            payload = self._read_unsafe()
            for student in payload.get("students", []):
                if int(student["id"]) == int(student_id):
                    return student
        return None

    def _read_unsafe(self) -> Dict:
        try:
            with open(self.json_path, "r", encoding="utf-8") as file:
                payload = json.load(file)
                if isinstance(payload, dict):
                    return payload
        except (json.JSONDecodeError, FileNotFoundError):
            pass
        return {"next_id": 1, "students": []}

    def _write_unsafe(self, payload: Dict) -> None:
        with open(self.json_path, "w", encoding="utf-8") as file:
            json.dump(payload, file, indent=2, ensure_ascii=False)

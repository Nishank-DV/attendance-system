import json
import logging
import os
import threading
from datetime import date, datetime, timezone
from typing import Dict, List, Optional, Tuple

import requests

from config import AppConfig


class AttendanceService:
    def __init__(self, json_path: str, cooldown_seconds: int) -> None:
        self.json_path = json_path
        self.cooldown_seconds = cooldown_seconds
        self._lock = threading.Lock()
        self._ensure_file()

    def _ensure_file(self) -> None:
        os.makedirs(os.path.dirname(self.json_path), exist_ok=True)
        if not os.path.exists(self.json_path):
            with self._lock:
                with open(self.json_path, "w", encoding="utf-8") as file:
                    json.dump({"active_date": None, "records_by_date": {}}, file, indent=2)

    def set_active_date(self, target_date: str) -> str:
        self._validate_date(target_date)

        with self._lock:
            payload = self._read_unsafe()
            payload["active_date"] = target_date
            payload.setdefault("records_by_date", {})
            payload["records_by_date"].setdefault(target_date, [])
            self._write_unsafe(payload)

        return target_date

    def get_active_date(self) -> str:
        with self._lock:
            payload = self._read_unsafe()
            active_date = payload.get("active_date")

        if active_date:
            return active_date

        return date.today().isoformat()

    def mark_attendance(self, student: Dict, confidence: float, target_date: Optional[str] = None) -> Dict:
        now = datetime.now(timezone.utc)
        current_date = target_date or self.get_active_date()
        self._validate_date(current_date)

        with self._lock:
            payload = self._read_unsafe()
            records_by_date = payload.setdefault("records_by_date", {})
            day_records = records_by_date.setdefault(current_date, [])
            last_record = self._get_last_record_for_student(day_records, int(student["id"]))

            if last_record is not None:
                last_ts = self._latest_timestamp(last_record)
                if last_ts and (now - last_ts).total_seconds() < self.cooldown_seconds:
                    self._notify_buzzer("cooldown")
                    return {
                        "status": "cooldown",
                        "student_id": student["id"],
                        "name": student["name"],
                        "confidence": confidence,
                        "message": "Cooldown active.",
                        "date": current_date,
                    }

            if last_record and not last_record.get("exit_time"):
                last_record["exit_time"] = now.isoformat()
                self._write_unsafe(payload)
                self._notify_buzzer("exit")
                return {
                    "status": "exit",
                    "student_id": student["id"],
                    "name": student["name"],
                    "confidence": confidence,
                    "timestamp": now.isoformat(),
                    "date": current_date,
                }

            new_entry = {
                "student_id": student["id"],
                "name": student["name"],
                "roll_number": student["roll_number"],
                "department": student["department"],
                "entry_time": now.isoformat(),
                "exit_time": "",
                "confidence": round(float(confidence), 2),
                "date": current_date,
            }
            day_records.append(new_entry)

            if not payload.get("active_date"):
                payload["active_date"] = current_date

            self._write_unsafe(payload)

        self._notify_buzzer("entry")
        return {
            "status": "entry",
            "student_id": student["id"],
            "name": student["name"],
            "confidence": confidence,
            "timestamp": now.isoformat(),
            "date": current_date,
        }

    def mark_unknown(self) -> None:
        self._notify_buzzer("unknown")

    def trigger_buzzer(self, pattern: str) -> Tuple[bool, str]:
        return self._notify_buzzer(pattern)

    def get_records(self, target_date: Optional[str] = None) -> List[Dict]:
        current_date = target_date or self.get_active_date()
        self._validate_date(current_date)

        with self._lock:
            payload = self._read_unsafe()
            day_records = payload.get("records_by_date", {}).get(current_date, [])

        return day_records

    def get_summary(self, target_date: Optional[str] = None) -> Dict:
        current_date = target_date or self.get_active_date()
        self._validate_date(current_date)
        records = self.get_records(current_date)

        total_entries = len(records)
        total_exits = sum(1 for record in records if record.get("exit_time"))
        present = sorted({record["name"] for record in records if not record.get("exit_time")})

        return {
            "date": current_date,
            "total_entries": total_entries,
            "total_exits": total_exits,
            "present_count": len(present),
            "present": present,
        }

    def _notify_buzzer(self, pattern: str) -> Tuple[bool, str]:
        try:
            url = f"{AppConfig.ESP32_BASE_URL}/buzzer"
            response = requests.post(url, json={"pattern": pattern}, timeout=2)

            if response.ok:
                return True, "Buzzer triggered."
            return False, f"ESP32 responded {response.status_code}."

        except Exception as exc:
            logging.warning("Buzzer request failed: %s", exc)
            return False, "Buzzer request failed."

    @staticmethod
    def _validate_date(target_date: str) -> None:
        try:
            date.fromisoformat(target_date)
        except ValueError as exc:
            raise ValueError("Date must be in YYYY-MM-DD format.") from exc

    @staticmethod
    def _get_last_record_for_student(records: List[Dict], student_id: int) -> Optional[Dict]:
        for record in reversed(records):
            if int(record.get("student_id", -1)) == int(student_id):
                return record
        return None

    @staticmethod
    def _latest_timestamp(record: Dict) -> Optional[datetime]:
        if record.get("exit_time"):
            return datetime.fromisoformat(record["exit_time"])
        if record.get("entry_time"):
            return datetime.fromisoformat(record["entry_time"])
        return None

    def _read_unsafe(self) -> Dict:
        try:
            with open(self.json_path, "r", encoding="utf-8") as file:
                payload = json.load(file)

            if isinstance(payload, list):
                migrated = {
                    "active_date": date.today().isoformat(),
                    "records_by_date": {date.today().isoformat(): payload},
                }
                return migrated

            if isinstance(payload, dict):
                payload.setdefault("active_date", None)
                payload.setdefault("records_by_date", {})
                return payload

        except (json.JSONDecodeError, FileNotFoundError):
            pass

        return {"active_date": None, "records_by_date": {}}

    def _write_unsafe(self, payload: Dict) -> None:
        with open(self.json_path, "w", encoding="utf-8") as file:
            json.dump(payload, file, indent=2, ensure_ascii=False)

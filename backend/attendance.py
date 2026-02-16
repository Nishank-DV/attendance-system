import logging
from datetime import datetime, timezone
from typing import Tuple

import requests

from config import AppConfig
from database import AttendanceStore


class AttendanceService:
    def __init__(self, store: AttendanceStore, cooldown_seconds: int) -> None:
        self.store = store
        self.cooldown_seconds = cooldown_seconds

    def mark_attendance(self, name: str, confidence: float) -> dict:
        now = datetime.now(timezone.utc)
        last = self.store.get_last_record(name)

        if last is not None:
            last_ts = self._latest_timestamp(last)
            if last_ts and (now - last_ts).total_seconds() < self.cooldown_seconds:
                return {
                    "status": "cooldown",
                    "name": name,
                    "confidence": confidence,
                    "message": "Cooldown active.",
                }

        if last and not last["exit_time"]:
            self.store.update_exit_time(name, now)
            self._notify_buzzer("exit")
            return {
                "status": "exit",
                "name": name,
                "confidence": confidence,
                "timestamp": now.isoformat(),
            }

        self.store.append_entry(name, now, confidence)
        self._notify_buzzer("entry")
        return {
            "status": "entry",
            "name": name,
            "confidence": confidence,
            "timestamp": now.isoformat(),
        }

    def trigger_buzzer(self, pattern: str) -> Tuple[bool, str]:
        return self._notify_buzzer(pattern)

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
    def _latest_timestamp(record: dict):
        if record["exit_time"]:
            return datetime.fromisoformat(record["exit_time"])
        if record["entry_time"]:
            return datetime.fromisoformat(record["entry_time"])
        return None
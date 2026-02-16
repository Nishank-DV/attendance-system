"""Attendance storage module using JSON with thread-safe operations."""
import json
import os
import threading
from datetime import date, datetime
from typing import List, Optional, Dict


class AttendanceStore:
    """Thread-safe JSON-based attendance storage."""

    def __init__(self, json_path: str = None) -> None:
        """
        Initialize attendance storage.
        
        Args:
            json_path: Path to JSON file. If None, uses backend/data/attendance.json
        """
        if json_path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            data_dir = os.path.join(base_dir, "data")
            json_path = os.path.join(data_dir, "attendance.json")
        
        self.json_path = json_path
        self._lock = threading.Lock()
        self._ensure_file()

    def _ensure_file(self) -> None:
        """Create JSON file and directory if they don't exist."""
        os.makedirs(os.path.dirname(self.json_path), exist_ok=True)

        if not os.path.exists(self.json_path):
            with self._lock:
                with open(self.json_path, "w", encoding="utf-8") as f:
                    json.dump([], f, indent=2)

    def append_entry(self, name: str, timestamp: datetime, confidence: float) -> None:
        """
        Append a new attendance entry.
        
        Args:
            name: Person's name
            timestamp: Entry timestamp
            confidence: Recognition confidence score
        """
        with self._lock:
            records = self._read_records_unsafe()
            
            new_entry = {
                "name": name,
                "entry_time": timestamp.isoformat(),
                "exit_time": "",
                "confidence": round(confidence, 2)
            }
            
            records.append(new_entry)
            self._write_records_unsafe(records)

    def update_exit_time(self, name: str, timestamp: datetime) -> None:
        """
        Update exit time for the last entry of a person.
        
        Args:
            name: Person's name
            timestamp: Exit timestamp
        """
        with self._lock:
            records = self._read_records_unsafe()
            
            # Find last entry for this person without exit_time
            for record in reversed(records):
                if record["name"] == name and not record.get("exit_time"):
                    record["exit_time"] = timestamp.isoformat()
                    break
            
            self._write_records_unsafe(records)

    def get_last_record(self, name: str) -> Optional[Dict]:
        """
        Get the last attendance record for a person.
        
        Args:
            name: Person's name
            
        Returns:
            Last record dict or None if not found
        """
        with self._lock:
            records = self._read_records_unsafe()
            
            for record in reversed(records):
                if record["name"] == name:
                    return record
            
            return None

    def get_all_records(self) -> List[Dict]:
        """
        Get all attendance records.
        
        Returns:
            List of all attendance records
        """
        with self._lock:
            return self._read_records_unsafe()

    def read_records(self) -> List[Dict]:
        """Alias for get_all_records() for backward compatibility."""
        return self.get_all_records()

    def get_daily_summary(self, target_date: date) -> Dict:
        """
        Get attendance summary for a specific date.
        
        Args:
            target_date: Date to summarize
            
        Returns:
            Summary dict with entries, exits, and present count
        """
        with self._lock:
            records = self._read_records_unsafe()
        
        total_entries = 0
        total_exits = 0
        present = set()

        for record in records:
            entry_time = self._parse_datetime(record.get("entry_time"))
            exit_time = self._parse_datetime(record.get("exit_time"))

            if entry_time and entry_time.date() == target_date:
                total_entries += 1
                present.add(record["name"])

            if exit_time and exit_time.date() == target_date:
                total_exits += 1
                present.discard(record["name"])

        return {
            "date": target_date.isoformat(),
            "total_entries": total_entries,
            "total_exits": total_exits,
            "present_count": len(present),
            "present": sorted(present),
        }

    def _read_records_unsafe(self) -> List[Dict]:
        """Read records without acquiring lock (internal use only)."""
        try:
            with open(self.json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _write_records_unsafe(self, records: List[Dict]) -> None:
        """Write records without acquiring lock (internal use only)."""
        with open(self.json_path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)

    @staticmethod
    def _parse_datetime(value: str) -> Optional[datetime]:
        """Parse ISO format datetime string."""
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except (ValueError, TypeError):
            return None

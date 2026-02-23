import time
from threading import Lock
from typing import Dict, Optional


class StreamState:
    def __init__(self, disconnect_timeout_seconds: int) -> None:
        self._lock = Lock()
        self._latest_frame: Optional[bytes] = None
        self._latest_result: Dict = {
            "status": "waiting_frame",
            "recognized": False,
            "message": "Waiting for ESP32 frames.",
            "updated_at": "",
        }
        self._last_frame_ts: float = 0.0
        self._disconnect_timeout_seconds = max(1, int(disconnect_timeout_seconds))

    def update_frame(self, frame_bytes: bytes) -> None:
        if not frame_bytes:
            return

        now = time.time()
        with self._lock:
            self._latest_frame = bytes(frame_bytes)
            self._last_frame_ts = now

    def set_latest_result(self, payload: Dict) -> None:
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        data = dict(payload or {})
        data["updated_at"] = now_iso
        with self._lock:
            self._latest_result = data

    def get_latest_result(self) -> Dict:
        with self._lock:
            return dict(self._latest_result)

    def get_latest_frame(self) -> Optional[bytes]:
        with self._lock:
            return self._latest_frame

    def stream_status(self) -> Dict:
        now = time.time()
        with self._lock:
            has_frame = self._latest_frame is not None
            age_seconds = now - self._last_frame_ts if self._last_frame_ts else None

        connected = bool(has_frame and age_seconds is not None and age_seconds <= self._disconnect_timeout_seconds)
        return {
            "connected": connected,
            "has_frame": has_frame,
            "age_seconds": round(age_seconds, 2) if age_seconds is not None else None,
            "timeout_seconds": self._disconnect_timeout_seconds,
        }

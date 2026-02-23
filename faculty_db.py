import json
import os
import threading
from datetime import datetime, timezone
from typing import Dict, Optional

from werkzeug.security import check_password_hash, generate_password_hash


class FacultyDB:
    def __init__(self, json_path: str) -> None:
        self.json_path = json_path
        self._lock = threading.Lock()
        self._ensure_file()

    def _ensure_file(self) -> None:
        os.makedirs(os.path.dirname(self.json_path), exist_ok=True)
        if not os.path.exists(self.json_path):
            with self._lock:
                with open(self.json_path, "w", encoding="utf-8") as file:
                    json.dump({"next_id": 1, "users": []}, file, indent=2)

    def ensure_default_user(self, username: str, password: str) -> None:
        if not username or not password:
            return
        if self.get_user(username):
            return
        self.create_user(username=username, password=password, is_admin=True)

    def create_user(self, username: str, password: str, is_admin: bool = False) -> Dict:
        username = username.strip()
        if not username or not password:
            raise ValueError("Username and password are required.")

        with self._lock:
            payload = self._read_unsafe()
            users = payload.get("users", [])

            if any(user["username"].lower() == username.lower() for user in users):
                raise ValueError("Username already exists.")

            user_id = int(payload.get("next_id", 1))
            now_iso = datetime.now(timezone.utc).isoformat()
            user = {
                "id": user_id,
                "username": username,
                "password_hash": generate_password_hash(password),
                "is_admin": bool(is_admin),
                "created_at": now_iso,
                "updated_at": now_iso,
            }

            users.append(user)
            payload["users"] = users
            payload["next_id"] = user_id + 1
            self._write_unsafe(payload)
            return user

    def verify_user(self, username: str, password: str) -> bool:
        user = self.get_user(username)
        if not user:
            return False
        return check_password_hash(user["password_hash"], password)

    def update_password(self, username: str, new_password: str) -> None:
        if not username or not new_password:
            raise ValueError("Username and new password are required.")

        with self._lock:
            payload = self._read_unsafe()
            users = payload.get("users", [])
            for user in users:
                if user["username"].lower() == username.lower():
                    user["password_hash"] = generate_password_hash(new_password)
                    user["updated_at"] = datetime.now(timezone.utc).isoformat()
                    self._write_unsafe(payload)
                    return

        raise ValueError("User not found.")

    def get_user(self, username: str) -> Optional[Dict]:
        if not username:
            return None

        with self._lock:
            payload = self._read_unsafe()
            for user in payload.get("users", []):
                if user["username"].lower() == username.lower():
                    if "is_admin" not in user:
                        user["is_admin"] = False
                    return user
        return None

    def _read_unsafe(self) -> Dict:
        try:
            with open(self.json_path, "r", encoding="utf-8") as file:
                payload = json.load(file)
                if isinstance(payload, dict):
                    return payload
        except (json.JSONDecodeError, FileNotFoundError):
            pass
        return {"next_id": 1, "users": []}

    def _write_unsafe(self, payload: Dict) -> None:
        with open(self.json_path, "w", encoding="utf-8") as file:
            json.dump(payload, file, indent=2, ensure_ascii=False)

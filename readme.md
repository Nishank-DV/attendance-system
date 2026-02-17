# SmartVision AI Attendance System

Production-ready AI attendance system with:
- Flask backend (modular architecture)
- Server-rendered frontend using Flask templates/static
- Face recognition via `face_recognition` + `dlib`
- Dynamic student registration (webcam capture)
- JSON-based student and attendance storage
- ESP32 buzzer integration for event feedback

---

## ✅ Current Architecture

All UI is now served directly by Flask (no Live Server required).

```text
smartvision-attendance/
├── backend/
│   ├── app.py
│   ├── config.py
│   ├── attendance_service.py
│   ├── recognition_service.py
│   ├── registration.py
│   ├── student_db.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   └── dashboard.py
│   ├── templates/
│   │   ├── faculty.html
│   │   ├── dashboard.html
│   │   └── index.html
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css
│   │   └── js/
│   │       ├── dashboard.js
│   │       └── attendance.js
│   ├── data/
│   │   ├── students.json
│   │   └── attendance.json
│   ├── utils.py
│   └── __init__.py
├── esp32/
│   └── esp32_cam.ino
├── requirements.txt
└── readme.md
```

---

## 🔐 Auth + Page Routing

- `GET /faculty` → Faculty login page
- `POST /faculty/login` → Faculty login submission
- `GET /faculty/logout` → Logout and clear session
- `GET /dashboard` → Faculty dashboard (protected)
- `GET /attendance` → Attendance page (protected)

If not logged in, protected routes redirect to `/faculty`.

---

## 🧠 Recognition & Attendance Flow

1. Faculty registers student from webcam in dashboard.
2. System extracts face encoding and stores it in `backend/data/students.json`.
3. Attendance page captures live image and sends it to `/api/recognize`.
4. Backend compares probe encoding against stored encodings.
5. If match:
   - attendance is marked by `student_id`
   - entry/exit logic is applied
   - cooldown is enforced
6. If no match: returns `unknown`/`unregistered` and triggers unknown buzzer pattern.

Attendance is grouped by date in `backend/data/attendance.json`.

---

## 📡 API Endpoints

### Faculty / Student APIs
- `POST /api/register-student`
- `GET /api/students`
- `POST /api/delete-student`
- `POST /api/set-date`
- `GET /api/faculty/session`
- `POST /api/faculty/login` (JSON session endpoint used by dashboard APIs)
- `POST /api/faculty/logout`

### Attendance APIs
- `POST /api/recognize`
- `GET /api/attendance?date=YYYY-MM-DD`
- `GET /api/summary?date=YYYY-MM-DD`
- `POST /api/trigger-buzzer`

---

## ⚙️ Setup & Run

### 1) Install dependencies
```bash
pip install -r requirements.txt
```

### 2) Configure environment
Copy `.env.example` to `.env` and set your values:

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Required keys in `.env`:
- `FLASK_SECRET_KEY`
- `HOST`
- `PORT`
- `FACE_TOLERANCE`
- `COOLDOWN_SECONDS`
- `ESP32_BASE_URL`

Optional keys for faculty account management:
- `FACULTY_USERNAME` (default admin bootstrap)
- `FACULTY_PASSWORD` (default admin bootstrap)
- `FACULTY_RESET_KEY` (required for password reset)

### 3) Run Flask backend
```bash
cd backend
python app.py
```

Server runs on:
- `http://<HOST>:<PORT>` (from `.env`)

### 4) Open app pages
- Faculty Login: `http://127.0.0.1:5000/faculty`
- Faculty Dashboard: `http://127.0.0.1:5000/dashboard`
- Attendance Page: `http://127.0.0.1:5000/attendance`

---

## 🔧 Environment Config

Configuration is loaded from `.env` using `python-dotenv` in `backend/config.py`.

Defaults are provided in code for local development, but production should set explicit values.

---

## 👤 Faculty Account Management

- Create account: `GET /faculty/register`
- Forgot password: `GET /faculty/forgot`

Password reset requires the `FACULTY_RESET_KEY` value from `.env`.
Faculty registration is admin-only; the default admin is created from `FACULTY_USERNAME` and `FACULTY_PASSWORD`.

---

## 🔔 ESP32 Buzzer Patterns

Triggered from backend attendance service:
- `entry`
- `exit`
- `unknown`
- `cooldown`

ESP32 endpoint expected:
- `POST {ESP32_BASE_URL}/buzzer` with JSON `{ "pattern": "entry|exit|unknown|cooldown" }`

---

## Notes

- Legacy static frontend folder and `known_faces` startup dependency were removed.
- Current system is fully dynamic and session-driven with Flask-rendered pages.

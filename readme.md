# SmartVision Attendance System

SmartVision is a Flask-based AI attendance application that uses face recognition for student entry/exit tracking, faculty authentication, and optional ESP32-CAM + buzzer integration.

## What this project does

- Faculty login/logout with session protection
- Admin bootstrap user creation from environment variables
- Student registration from webcam image (`name`, `roll_number`, `department`)
- Face encoding storage in JSON (`backend/data/students.json`)
- Attendance marking with entry/exit toggle and cooldown logic
- Date-wise attendance storage and summary (`backend/data/attendance.json`)
- ESP32 mode polling + buzzer trigger integration

## Project structure

```text
smartvision-attendance/
├── .env.example
├── requirements.txt
├── readme.md
├── backend/
│   ├── app.py
│   ├── config.py
│   ├── attendance_service.py
│   ├── recognition_service.py
│   ├── registration.py
│   ├── student_db.py
│   ├── faculty_db.py
│   ├── utils.py
│   ├── routes/
│   │   ├── auth.py
│   │   └── dashboard.py
│   ├── templates/
│   │   ├── faculty.html
│   │   ├── faculty_register.html
│   │   ├── faculty_forgot.html
│   │   ├── dashboard.html
│   │   └── index.html
│   ├── static/
│   │   ├── css/style.css
│   │   └── js/
│   │       ├── dashboard.js
│   │       └── attendance.js
│   ├── data/
│   │   ├── students.json
│   │   ├── attendance.json
│   │   └── faculty_users.json
│   └── received_images/
└── esp32/
      └── esp32_cam.ino
```

## Prerequisites

- Python 3.10+ (recommended)
- `pip`
- Webcam (for registration and attendance via browser)
- Modern browser (Chrome/Edge recommended)
- Optional: ESP32-CAM module for hardware integration

> Note: this project uses `dlib-bin` (prebuilt wheels) to reduce native build issues. If installation still fails on your platform, install C++ build tools and retry.

## Full setup (new system / exported project)

Run all commands from project root: `smartvision-attendance`.

### Windows quick commands (recommended)

Use these exact commands in PowerShell:

```powershell
Set-Location "C:\Users\<YOUR_USER>\...\smartvision-attendance"
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\setup.ps1
.\run.ps1
```

Open: `http://127.0.0.1:5000/faculty`

### 1) Create virtual environment

Windows (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2) Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3) Configure environment variables

Copy `.env.example` to `.env`.

Windows (PowerShell):

```powershell
Copy-Item .env.example .env
```

Linux/macOS:

```bash
cp .env.example .env
```

Then fill values in `.env`:

| Key | Description | Example |
|---|---|---|
| `FLASK_SECRET_KEY` | Flask session secret | `super-secret-key` |
| `HOST` | Bind host | `0.0.0.0` |
| `PORT` | Backend port | `5000` |
| `FACE_TOLERANCE` | Recognition threshold | `0.6` |
| `COOLDOWN_SECONDS` | Cooldown between marks | `120` |
| `ESP32_BASE_URL` | ESP32 endpoint base | `http://192.168.1.50` |
| `FACULTY_USERNAME` | Default admin username | `faculty` |
| `FACULTY_PASSWORD` | Default admin password | `faculty123` |
| `FACULTY_RESET_KEY` | Key for forgot-password reset | `reset123` |

If any key is left empty, `backend/config.py` fallback defaults are used.

### 4) Run the backend

```bash
cd backend
python app.py
```

Backend starts at:

- `http://127.0.0.1:5000` (if default host/port)

## Application usage flow

### Step 1: Faculty login

- Open `http://127.0.0.1:5000/faculty`
- Login with admin credentials from `.env` (`FACULTY_USERNAME`, `FACULTY_PASSWORD`)

### Step 2: Register students

- Open Dashboard: `http://127.0.0.1:5000/dashboard`
- Set attendance date (optional; otherwise active/default date is used)
- Click **Start Camera** and grant browser permission
- Enter `Name`, `Roll Number`, `Department`
- Click **Capture & Register**
- Registered students are saved in `backend/data/students.json`

### Step 3: Mark attendance

- Open Attendance page: `http://127.0.0.1:5000/attendance`
- Click **Start Camera**
- Click **Capture & Recognize**
- System marks either:
   - `entry` (first detection)
   - `exit` (next valid detection)
   - `cooldown` (if scanned too soon)
   - `unknown` or `no_face`

### Step 4: View reports

- Attendance table and stats are loaded from backend APIs
- Date-based records are stored in `backend/data/attendance.json`

## Faculty account management

- Register new faculty (admin only): `GET /faculty/register`
- Forgot/reset password: `GET /faculty/forgot`
- Reset requires correct `FACULTY_RESET_KEY`

## Key API endpoints

### Pages

- `GET /` (redirects by login status)
- `GET /faculty`
- `POST /faculty/login`
- `GET /faculty/logout`
- `GET /dashboard` (protected)
- `GET /attendance` (protected)

### Faculty/Student APIs

- `POST /api/faculty/login`
- `POST /api/faculty/logout`
- `GET /api/faculty/session`
- `POST /api/register-student`
- `GET /api/students`
- `POST /api/delete-student`

### Attendance APIs

- `POST /api/recognize` (also mapped to `/recognize` and `/upload`)
- `GET /api/attendance?date=YYYY-MM-DD`
- `POST /api/set-date`
- `GET /api/summary?date=YYYY-MM-DD`
- `POST /api/trigger-buzzer`

### Device control APIs

- `GET /device_mode`
- `GET /set_mode/idle`
- `GET /set_mode/register`
- `GET /set_mode/attendance`
- `GET /health`

## ESP32-CAM integration procedure (optional)

### 1) Prepare Arduino IDE

- Install ESP32 board package (Espressif)
- Select board model matching your ESP32-CAM
- Open `esp32/esp32_cam.ino`

### 2) Edit firmware config

In `AppConfig` inside `esp32_cam.ino`, set:

- `wifiSsid`
- `wifiPassword`
- `backendBaseUrl` (example: `http://192.168.1.100:5000`)

### 3) Flash and monitor

- Upload firmware
- Open Serial Monitor (115200 baud)
- Note ESP32 IP address after Wi-Fi connection

### 4) Link backend to ESP32 buzzer endpoint

Set `.env` key:

- `ESP32_BASE_URL=http://<esp32-ip>`

Backend sends buzzer patterns to `POST /buzzer` on ESP32:

- `entry`, `exit`, `unknown`, `cooldown`

## Data files generated/used

- `backend/data/students.json` → student profiles + encodings
- `backend/data/attendance.json` → active date + date-wise attendance records
- `backend/data/faculty_users.json` → faculty users with hashed passwords

## Export checklist (run anywhere)

When moving project to another machine, make sure these are present:

1. Full project folder including `backend/`, `esp32/`, `.env.example`, `requirements.txt`
2. New virtual environment created on target machine
3. Dependencies installed via `pip install -r requirements.txt`
4. `.env` created and configured
5. Backend started with `python backend/app.py` or `cd backend && python app.py`

## Troubleshooting

- **`ModuleNotFoundError`**: activate virtual environment and reinstall requirements.
- **`face_recognition` or `dlib-bin` install fails**: update pip (`python -m pip install --upgrade pip`) and retry; if needed, install compiler/build tools and retry.
- **Camera not opening in browser**: use `http://127.0.0.1:5000` or HTTPS and allow camera permission.
- **Unauthorized API response (401)**: login again from `/faculty`.
- **ESP32 buzzer not triggering**: check `ESP32_BASE_URL`, same network, and ESP32 `/buzzer` route availability.

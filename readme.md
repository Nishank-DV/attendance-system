# 🔍 SmartVision AI Attendance System

A production-ready **face recognition attendance platform** with real-time webcam capture, ESP32-CAM integration, automated entry/exit tracking, and a modern web dashboard.

---

## 📋 Table of Contents

- [Features](#-features)
- [Project Structure](#-project-structure)
- [How It Works](#-how-it-works)
- [Installation](#-installation)
- [How to Run](#-how-to-run-the-application)
- [ESP32 Integration](#-esp32-cam-integration)
- [API Documentation](#-api-documentation)
- [Demo Flow](#-demo-flow)
- [Troubleshooting](#-troubleshooting)

---

## ✨ Features

### 🎯 Core Features
- **Real-time Face Recognition** using `face_recognition` library
- **Live Webcam Capture** with HTML5 getUserMedia API
- **Smart Cooldown System** - prevents duplicate entries within 2 minutes
- **Entry/Exit Tracking** - automatic detection of check-in and check-out
- **Confidence Scoring** - percentage-based accuracy for each recognition
- **JSON Storage** - thread-safe attendance record management
- **Daily Summary** - real-time statistics and analytics

### 🎨 Frontend Features
- Modern professional UI with gradient animations
- Live webcam feed with capture button
- Color-coded status indicators (Entry, Exit, Unknown, No Face)
- Real-time attendance table
- Auto-refresh every 5 seconds
- Responsive design for mobile and desktop
- Loading spinners and smooth transitions

### 🤖 ESP32-CAM Integration
- MJPEG stream support
- Automated buzzer control on GPIO 12
- Different beep patterns:
  - **Entry** → 1 short beep
  - **Exit** → 2 short beeps
  - **Unknown** → 1 long beep
  - **Error** → 3 rapid beeps

---

## 📁 Project Structure

```
smartvision-attendance/
│
├── backend/                        # Flask backend server
│   ├── app.py                      # Main Flask application (entry point)
│   ├── config.py                   # Configuration settings
│   ├── recognition.py              # Face recognition module
│   ├── attendance.py               # Attendance logic & cooldown system
│   ├── database.py                 # JSON storage (thread-safe)
│   ├── utils.py                    # Logging utilities
│   └── data/
│       └── attendance.json         # Attendance records storage
│
├── frontend/                       # Web interface
│   ├── index.html                  # Main dashboard
│   ├── style.css                   # Styling & animations
│   └── script.js                   # Webcam capture & API integration
│
├── esp32/                          # ESP32-CAM firmware
│   └── esp32_cam.ino              # Arduino sketch for camera module
│
├── known_faces/                    # Face training database
│   ├── PersonName1/
│   │   ├── photo1.jpg
│   │   └── photo2.jpg
│   └── PersonName2/
│       └── photo.jpg
│
├── attendance_records/             # Legacy CSV storage (optional)
│   └── attendance.csv
│
├── requirements.txt                # Python dependencies
├── README.md                       # This file
└── .gitignore                      # Git ignore rules
```

---

## 🔬 How It Works

### 📸 Face Recognition Flow

1. **Training Phase (Startup)**
   - Backend loads all images from `known_faces/` directory
   - Face encodings are extracted and stored in memory
   - Each person's name is mapped from their folder name

2. **Recognition Phase (Real-time)**
   - Webcam captures a frame or ESP32-CAM streams video
   - Frame is sent to backend `/api/recognize` endpoint
   - Backend extracts face encoding from the image
   - Compares against all known face encodings using `face_distance`
   - If distance < 0.6 threshold → Person recognized
   - If distance ≥ 0.6 → Unknown person
   - If no face detected → "No Face" status

3. **Confidence Calculation**
   ```python
   confidence = (1 - face_distance) * 100
   ```
   - Distance of 0.0 = 100% confidence
   - Distance of 0.6 = 0% confidence (threshold)

### 📊 Attendance Logic

#### Entry/Exit Detection Algorithm

```python
When a face is recognized:
1. Check last attendance record for this person
2. If last record exists:
   a. Check if exit_time is empty
   b. If empty → Mark EXIT (person is leaving)
   c. If filled → Mark ENTRY (person is arriving)
3. If no record → Mark ENTRY (first time today)
```

#### Smart Cooldown System

- Prevents duplicate entries within **2 minutes**
- If person tries to scan again within cooldown → Status: `cooldown`
- Cooldown applies to the latest timestamp (entry or exit)

#### Data Flow

```
Webcam → Capture Image → Backend API → Face Recognition
    ↓
Recognition Result (name + confidence)
    ↓
Attendance Service → Check Cooldown → Determine Entry/Exit
    ↓
Database → Save to JSON → Return Response
    ↓
Frontend → Display Result → Refresh Table
```

### 🔔 ESP32 Buzzer Integration

The ESP32-CAM can be integrated to:
1. Stream live video feed (MJPEG)
2. Trigger audio feedback for recognition events

**Backend Integration:**
```python
# In attendance.py
def _notify_buzzer(self, pattern: str):
    url = f"{ESP32_BASE_URL}/buzzer"
    response = requests.post(url, json={"pattern": pattern}, timeout=2)
```

**ESP32 Endpoints:**
- `/stream` - GET - MJPEG video stream
- `/buzzer` - POST - Trigger buzzer pattern

---

## 💾 Installation

### Prerequisites
- Python 3.10+
- pip (Python package manager)
- Webcam (for frontend) or ESP32-CAM module
- Modern web browser (Chrome, Firefox, Edge)

### Step 1: Clone or Download Project
```bash
cd smartvision-attendance
```

### Step 2: Install Python Dependencies
```bash
pip install -r requirements.txt
```

### Required Packages:
```txt
flask==3.0.2
flask-cors==4.0.0
face_recognition==1.3.0
dlib==19.24.0
Pillow==10.2.0
numpy==1.26.4
requests==2.31.0
```

**Note for Windows Users:**
- Installing `dlib` might require Microsoft Visual C++ Build Tools
- Alternative: Install pre-built wheel from [unofficial binaries](https://github.com/z-mahmud22/Dlib_Windows_Python3.x)

### Step 3: Add Known Faces
Create folders inside `known_faces/` with person names:

```
known_faces/
├── Alice/
│   ├── alice1.jpg
│   ├── alice2.jpg
│   └── alice3.jpg
├── Bob/
│   └── bob.jpg
└── Charlie/
    ├── front.jpg
    └── side.jpg
```

**Tips for Best Recognition:**
- Use clear, front-facing photos
- Good lighting
- Multiple angles per person (recommended)
- Image formats: `.jpg`, `.jpeg`, `.png`

---

## 🚀 HOW TO RUN THE APPLICATION

### Backend (Flask API Server)

1. **Navigate to backend folder:**
   ```bash
   cd backend
   ```

2. **Install dependencies (if not done):**
   ```bash
   pip install -r ../requirements.txt
   ```

3. **Run the Flask server:**
   ```bash
   python app.py
   ```

4. **Expected Output:**
   ```
   2026-02-16 10:30:00,000 | INFO | root | Loading known faces...
   2026-02-16 10:30:00,500 | INFO | root | Loaded 3 known faces
   2026-02-16 10:30:00,501 | INFO | root | ==================================================
   2026-02-16 10:30:00,501 | INFO | root | SmartVision Attendance Backend is Running ✅
   2026-02-16 10:30:00,501 | INFO | root | ==================================================
    * Serving Flask app 'app'
    * Running on http://127.0.0.1:5000
   ```

5. **Backend will be accessible at:**
   - Local: `http://127.0.0.1:5000`
   - Network: `http://YOUR_IP:5000`

---

### Frontend (Web Dashboard)

**Option 1: Direct File Open**
1. Navigate to `frontend/` folder
2. Right-click `index.html` → Open with Chrome/Firefox
3. Grant webcam permissions when prompted

**Option 2: Live Server (Recommended)**
1. Install VS Code extension: "Live Server"
2. Right-click `index.html` → "Open with Live Server"
3. Browser opens automatically at `http://127.0.0.1:5500`

**Option 3: Python HTTP Server**
```bash
cd frontend
python -m http.server 8000
# Open browser: http://localhost:8000
```

**Frontend Features:**
- Click **"Start Camera"** to activate webcam
- Click **"Capture & Recognize"** to scan face
- View results instantly with color-coded status
- Attendance table auto-refreshes every 5 seconds

---

### ESP32-CAM (Optional)

1. **Open Arduino IDE**
2. **Load sketch:**
   - File → Open → `esp32/esp32_cam.ino`

3. **Configure WiFi credentials:**
   ```cpp
   const char *ssid = "YOUR_WIFI_SSID";
   const char *password = "YOUR_WIFI_PASSWORD";
   const char *backendUrl = "http://YOUR_PC_IP:5000/api/recognize";
   ```

4. **Select board:**
   - Tools → Board → ESP32 Arduino → AI Thinker ESP32-CAM

5. **Upload code**

6. **Update backend config:**
   Edit `backend/config.py`:
   ```python
   ESP32_BASE_URL = "http://ESP32_IP_ADDRESS"
   ```

7. **Restart backend:**
   ```bash
   python app.py
   ```

8. **ESP32 Features:**
   - MJPEG stream: `http://ESP32_IP/stream`
   - Buzzer control: `POST http://ESP32_IP/buzzer`

---

## 📡 API Documentation

### Base URL
```
http://127.0.0.1:5000
```

### Endpoints

#### 1. Health Check
```http
GET /
```
**Response:**
```
SmartVision Attendance Backend is Running ✅
```

---

#### 2. Recognize Face
```http
POST /api/recognize
```

**Request (multipart/form-data):**
```
image: [binary file]
```

**Request (JSON with base64):**
```json
{
  "image_base64": "data:image/jpeg;base64,/9j/4AAQ..."
}
```

**Response Examples:**

**Entry:**
```json
{
  "status": "entry",
  "name": "Alice",
  "confidence": 95.23,
  "timestamp": "2026-02-16T10:30:00.000Z"
}
```

**Exit:**
```json
{
  "status": "exit",
  "name": "Alice",
  "confidence": 92.71,
  "timestamp": "2026-02-16T18:30:00.000Z"
}
```

**Unknown:**
```json
{
  "status": "unknown"
}
```

**No Face:**
```json
{
  "status": "no_face"
}
```

**Cooldown:**
```json
{
  "status": "cooldown",
  "name": "Alice",
  "confidence": 94.50,
  "message": "Cooldown active."
}
```

---

#### 3. Get Attendance Records
```http
GET /api/attendance
```

**Response:**
```json
{
  "records": [
    {
      "name": "Alice",
      "entry_time": "2026-02-16T09:00:00",
      "exit_time": "2026-02-16T17:00:00",
      "confidence": 95.23
    },
    {
      "name": "Bob",
      "entry_time": "2026-02-16T09:15:00",
      "exit_time": "",
      "confidence": 92.45
    }
  ]
}
```

---

#### 4. Get Daily Summary
```http
GET /api/summary
```

**Response:**
```json
{
  "date": "2026-02-16",
  "total_entries": 25,
  "total_exits": 20,
  "present_count": 5,
  "present": ["Alice", "Bob", "Charlie", "David", "Eve"]
}
```

---

#### 5. Trigger Buzzer (ESP32)
```http
POST /api/trigger-buzzer
```

**Request:**
```json
{
  "pattern": "entry"
}
```

**Patterns:** `entry`, `exit`, `unknown`, `error`

**Response:**
```json
{
  "status": "ok",
  "message": "Buzzer triggered."
}
```

---

## 🎬 Demo Flow

### Scenario: Employee Check-in

1. **Morning Arrival (9:00 AM)**
   - Alice stands in front of webcam
   - Clicks "Capture & Recognize"
   - Backend recognizes: `Alice` with 95% confidence
   - No previous entry today → Status: **`entry`**
   - Database saves:
     ```json
     {
       "name": "Alice",
       "entry_time": "2026-02-16T09:00:00",
       "exit_time": "",
       "confidence": 95.23
     }
     ```
   - ESP32 buzzer: **1 short beep** ✅
   - Frontend shows: Green "Entry Recorded" card

2. **Lunch Break Out (12:30 PM)**
   - Alice scans again
   - Backend finds last record with empty `exit_time`
   - Status: **`exit`**
   - Database updates:
     ```json
     {
       "name": "Alice",
       "entry_time": "2026-02-16T09:00:00",
       "exit_time": "2026-02-16T12:30:00",
       "confidence": 94.12
     }
     ```
   - ESP32 buzzer: **2 short beeps** 🚪
   - Frontend shows: Red "Exit Recorded" card

3. **Lunch Break Return (1:00 PM)**
   - Alice scans after lunch
   - Last record has `exit_time` filled
   - Status: **`entry`** (new entry)
   - New record created

4. **Cooldown Test (1:01 PM)**
   - Alice tries to scan again immediately
   - Less than 2 minutes since last scan
   - Status: **`cooldown`**
   - No database change
   - Frontend shows: "Cooldown Active" message

5. **Unknown Person**
   - Stranger stands in front of camera
   - Face distance > 0.6 threshold
   - Status: **`unknown`**
   - No database entry
   - ESP32 buzzer: **1 long beep** ⚠️
   - Frontend shows: Yellow "Not Recognized" card

---

## 🔧 Troubleshooting

### Backend Issues

#### Problem: `ModuleNotFoundError: No module named 'face_recognition'`
**Solution:**
```bash
pip install face_recognition
```
If error persists on Windows:
```bash
pip install cmake
pip install dlib
pip install face_recognition
```

---

#### Problem: `Loaded 0 known faces`
**Solution:**
1. Check `known_faces/` folder exists
2. Ensure subfolders contain `.jpg/.jpeg/.png` images
3. Verify folder structure:
   ```
   known_faces/
   └── PersonName/
       └── photo.jpg
   ```

---

#### Problem: Backend not starting (Port already in use)
**Solution:**
```bash
# Change port in config.py
PORT = 5001  # or any available port
```

---

### Frontend Issues

#### Problem: Camera not working
**Solution:**
1. Grant camera permissions in browser
2. Check if camera is being used by another app
3. Try different browser (Chrome recommended)
4. Check browser console for errors (F12)

---

#### Problem: "Backend Offline" status
**Solution:**
1. Ensure backend is running on port 5000
2. Check firewall settings
3. Verify API_BASE_URL in `script.js`:
   ```javascript
   const API_BASE_URL = 'http://127.0.0.1:5000';
   ```
4. Test backend: Open `http://127.0.0.1:5000` in browser

---

#### Problem: CORS error in browser console
**Solution:**
Backend already has CORS enabled. If issue persists:
```python
# In app.py, ensure CORS is configured:
from flask_cors import CORS
app = Flask(__name__)
CORS(app)  # This line enables CORS
```

---

### Recognition Issues

#### Problem: Low confidence scores (<70%)
**Solution:**
1. Add more photos of the person (3-5 recommended)
2. Use better lighting for training photos
3. Ensure photos are clear and front-facing
4. Adjust tolerance in `config.py`:
   ```python
   FACE_TOLERANCE = 0.5  # Lower = stricter matching
   ```

---

#### Problem: Always returning "Unknown"
**Solution:**
1. Verify photos are in correct folder structure
2. Restart backend to reload face encodings
3. Check logs for face loading errors
4. Test with high-quality photos first

---

### ESP32-CAM Issues

#### Problem: Can't connect to WiFi
**Solution:**
1. Verify SSID and password in code
2. Check WiFi is 2.4GHz (ESP32 doesn't support 5GHz)
3. Open Serial Monitor to see connection status

---

#### Problem: Buzzer not working
**Solution:**
1. Check buzzer wiring to GPIO 12
2. Verify ESP32_BASE_URL in` backend/config.py`
3. Test buzzer endpoint manually:
   ```bash
   curl -X POST http://ESP32_IP/buzzer -d '{"pattern":"entry"}'
   ```

---

## 🛠️ Configuration

### Backend (`backend/config.py`)

```python
HOST = "0.0.0.0"              # Listen on all interfaces
PORT = 5000                    # Flask server port
LOG_LEVEL = "INFO"             # Logging level

FACE_TOLERANCE = 0.6           # Recognition threshold (lower = stricter)
COOLDOWN_SECONDS = 120         # Cooldown period in seconds

ESP32_BASE_URL = "http://192.168.4.1"  # ESP32-CAM IP address
```

### Frontend (`frontend/script.js`)

```javascript
const API_BASE_URL = 'http://127.0.0.1:5000';  // Backend URL
const REFRESH_INTERVAL = 5000;                  // Auto-refresh interval (ms)
```

---

## 📊 Database Schema

**File:** `backend/data/attendance.json`

**Format:**
```json
[
  {
    "name": "Alice",
    "entry_time": "2026-02-16T09:00:00",
    "exit_time": "2026-02-16T17:00:00",
    "confidence": 95.23
  }
]
```

**Fields:**
- `name` (string): Person's name from folder name
- `entry_time` (ISO 8601): Entry timestamp
- `exit_time` (ISO 8601): Exit timestamp (empty string if not exited)
- `confidence` (float): Recognition confidence percentage

---

## 🔐 Security Notes

1. **Local Network Only**
   - Default configuration runs on localhost
   - For network access, update `HOST` in config.py
   - Consider authentication for production use

2. **Face Data Privacy**
   - Face encodings stored in memory only
   - Original images remain in `known_faces/` folder
   - Attendance records in local JSON file

3. **Production Deployment**
   - Use HTTPS for remote access
   - Add authentication middleware
   - Implement rate limiting
   - Use production WSGI server (gunicorn/waitress)

---

## 📝 License

This project is provided as-is for educational and internal use.

---

## 🙏 Acknowledgments

- **face_recognition** by Adam Geitgey
- **dlib** by Davis King
- **Flask** web framework
- ESP32-CAM community

---

## 📞 Support

For issues and questions:
1. Check [Troubleshooting](#-troubleshooting) section
2. Review backend logs for error messages
3. Verify all dependencies are installed correctly

---

**🎉 Congratulations! Your SmartVision AI Attendance System is now ready to use!**
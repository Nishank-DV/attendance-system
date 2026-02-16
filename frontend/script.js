// ===== CONFIGURATION =====
const API_BASE_URL = 'http://127.0.0.1:5000';
const REFRESH_INTERVAL = 5000; // 5 seconds

// ===== STATE =====
let cameraStream = null;
let isCameraActive = false;
let isProcessing = false;

// ===== DOM ELEMENTS =====
const elements = {
    // Camera
    webcam: document.getElementById('webcam'),
    canvas: document.getElementById('canvas'),
    placeholder: document.getElementById('webcam-placeholder'),
    toggleCamera: document.getElementById('toggle-camera'),
    captureBtn: document.getElementById('capture-btn'),
    captureText: document.getElementById('capture-text'),
    captureSpinner: document.getElementById('capture-spinner'),
    
    // Result
    resultSection: document.getElementById('result-section'),
    resultContent: document.getElementById('result-content'),
    
    // Table
    attendanceTable: document.getElementById('attendance-table'),
    refreshBtn: document.getElementById('refresh-btn'),
    
    // Stats
    statEntries: document.getElementById('stat-entries'),
    statExits: document.getElementById('stat-exits'),
    statPresent: document.getElementById('stat-present'),
    
    // Status
    backendStatus: document.getElementById('backend-status'),
    backendUrl: document.getElementById('backend-url')
};

// ===== INITIALIZATION =====
document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
});

async function initializeApp() {
    console.log('🚀 Initializing SmartVision AI Attendance System...');
    
    // Set backend URL in footer
    elements.backendUrl.textContent = API_BASE_URL;
    
    // Check backend connection
    await checkBackendConnection();
    
    // Setup event listeners
    setupEventListeners();
    
    // Load attendance data
    await loadAttendanceData();
    await loadSummaryStats();
    
    // Start auto-refresh
    startAutoRefresh();
    
    console.log('✅ Application initialized successfully');
}

// ===== EVENT LISTENERS =====
function setupEventListeners() {
    elements.toggleCamera.addEventListener('click', toggleCamera);
    elements.captureBtn.addEventListener('click', captureAndRecognize);
    elements.refreshBtn.addEventListener('click', () => {
        loadAttendanceData();
        loadSummaryStats();
    });
}

// ===== BACKEND CONNECTION =====
async function checkBackendConnection() {
    try {
        const response = await fetch(`${API_BASE_URL}/`);
        if (response.ok) {
            updateBackendStatus(true);
            return true;
        }
    } catch (error) {
        console.error('❌ Backend connection failed:', error);
    }
    updateBackendStatus(false);
    return false;
}

function updateBackendStatus(connected) {
    if (connected) {
        elements.backendStatus.classList.add('connected');
        elements.backendStatus.innerHTML = '<span class="status-dot"></span><span>Backend Connected</span>';
    } else {
        elements.backendStatus.classList.remove('connected');
        elements.backendStatus.innerHTML = '<span class="status-dot"></span><span>Backend Offline</span>';
    }
}

// ===== CAMERA MANAGEMENT =====
async function toggleCamera() {
    if (isCameraActive) {
        stopCamera();
    } else {
        await startCamera();
    }
}

async function startCamera() {
    try {
        cameraStream = await navigator.mediaDevices.getUserMedia({
            video: {
                width: { ideal: 1280 },
                height: { ideal: 720 },
                facingMode: 'user'
            }
        });
        
        elements.webcam.srcObject = cameraStream;
        elements.placeholder.style.display = 'none';
        elements.webcam.style.display = 'block';
        elements.toggleCamera.textContent = 'Stop Camera';
        elements.captureBtn.disabled = false;
        isCameraActive = true;
        
        console.log('📷 Camera started successfully');
    } catch (error) {
        console.error('❌ Failed to start camera:', error);
        alert('Failed to access camera. Please check permissions.');
    }
}

function stopCamera() {
    if (cameraStream) {
        cameraStream.getTracks().forEach(track => track.stop());
        elements.webcam.srcObject = null;
        elements.webcam.style.display = 'none';
        elements.placeholder.style.display = 'flex';
        elements.toggleCamera.textContent = 'Start Camera';
        elements.captureBtn.disabled = true;
        isCameraActive = false;
        cameraStream = null;
        
        console.log('⏹️ Camera stopped');
    }
}

// ===== CAPTURE & RECOGNIZE =====
async function captureAndRecognize() {
    if (isProcessing || !isCameraActive) return;
    
    isProcessing = true;
    elements.captureBtn.disabled = true;
    elements.captureText.style.display = 'none';
    elements.captureSpinner.style.display = 'block';
    
    try {
        // Capture frame from webcam
        const imageBlob = await captureFrame();
        
        // Send to backend
        const result = await recognizeFace(imageBlob);
        
        // Display result
        displayResult(result);
        
        // Refresh attendance data
        await loadAttendanceData();
        await loadSummaryStats();
        
    } catch (error) {
        console.error('❌ Recognition failed:', error);
        showError('Recognition failed. Please try again.');
    } finally {
        isProcessing = false;
        elements.captureBtn.disabled = false;
        elements.captureText.style.display = 'block';
        elements.captureSpinner.style.display = 'none';
    }
}

async function captureFrame() {
    const canvas = elements.canvas;
    const video = elements.webcam;
    
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0);
    
    return new Promise((resolve) => {
        canvas.toBlob((blob) => {
            resolve(blob);
        }, 'image/jpeg', 0.95);
    });
}

async function recognizeFace(imageBlob) {
    const formData = new FormData();
    formData.append('image', imageBlob, 'capture.jpg');
    
    const response = await fetch(`${API_BASE_URL}/api/recognize`, {
        method: 'POST',
        body: formData
    });
    
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return await response.json();
}

// ===== DISPLAY RESULTS =====
function displayResult(result) {
    const status = result.status;
    let html = '';
    
    if (status === 'entry' || status === 'exit') {
        // Recognized person
        const icon = status === 'entry' ? '✅' : '🚪';
        const statusText = status.charAt(0).toUpperCase() + status.slice(1);
        
        html = `
            <div class="result-icon">${icon}</div>
            <div class="result-name">${result.name}</div>
            <span class="result-status ${status}">${statusText} Recorded</span>
            <p class="result-confidence">Confidence: ${result.confidence}%</p>
            <div class="confidence-bar">
                <div class="confidence-fill" style="width: ${result.confidence}%"></div>
            </div>
        `;
    } else if (status === 'cooldown') {
        // Cooldown active
        html = `
            <div class="result-icon">⏱️</div>
            <div class="result-name">${result.name}</div>
            <span class="result-status entry">Cooldown Active</span>
            <p class="result-confidence">${result.message}</p>
        `;
    } else if (status === 'unknown') {
        // Unknown face
        html = `
            <div class="result-icon">❓</div>
            <div class="result-name">Unknown Person</div>
            <span class="result-status unknown">Not Recognized</span>
            <p class="result-confidence">No matching face found in database</p>
        `;
    } else if (status === 'no_face') {
        // No face detected
        html = `
            <div class="result-icon">🔍</div>
            <div class="result-name">No Face Detected</div>
            <span class="result-status no_face">No Face</span>
            <p class="result-confidence">Please ensure your face is visible</p>
        `;
    } else {
        // Error
        html = `
            <div class="result-icon">⚠️</div>
            <div class="result-name">Error</div>
            <span class="result-status unknown">Recognition Failed</span>
            <p class="result-confidence">${result.message || 'An error occurred'}</p>
        `;
    }
    
    elements.resultContent.innerHTML = html;
    elements.resultSection.style.display = 'block';
    
    // Auto-hide after 10 seconds
    setTimeout(() => {
        elements.resultSection.style.display = 'none';
    }, 10000);
}

function showError(message) {
    elements.resultContent.innerHTML = `
        <div class="result-icon">⚠️</div>
        <div class="result-name">Error</div>
        <span class="result-status unknown">Failed</span>
        <p class="result-confidence">${message}</p>
    `;
    elements.resultSection.style.display = 'block';
    
    setTimeout(() => {
        elements.resultSection.style.display = 'none';
    }, 5000);
}

// ===== LOAD ATTENDANCE DATA =====
async function loadAttendanceData() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/attendance`);
        if (!response.ok) throw new Error('Failed to load attendance');
        
        const data = await response.json();
        renderAttendanceTable(data.records);
    } catch (error) {
        console.error('❌ Failed to load attendance:', error);
        elements.attendanceTable.innerHTML = `
            <tr>
                <td colspan="5" style="text-align: center; padding: 40px; color: var(--danger);">
                    Failed to load attendance records
                </td>
            </tr>
        `;
    }
}

function renderAttendanceTable(records) {
    if (!records || records.length === 0) {
        elements.attendanceTable.innerHTML = `
            <tr>
                <td colspan="5" style="text-align: center; padding: 40px;">
                    No attendance records yet
                </td>
            </tr>
        `;
        return;
    }
    
    // Reverse to show latest first
    const sortedRecords = [...records].reverse();
    
    let html = '';
    sortedRecords.forEach(record => {
        const entryTime = record.entry_time ? formatDateTime(record.entry_time) : '--';
        const exitTime = record.exit_time ? formatDateTime(record.exit_time) : '--';
        const status = record.exit_time ? 'left' : 'present';
        const statusText = record.exit_time ? 'Left' : 'Present';
        
        html += `
            <tr>
                <td><strong>${record.name}</strong></td>
                <td>${entryTime}</td>
                <td>${exitTime}</td>
                <td>${record.confidence}%</td>
                <td><span class="status-tag ${status}">${statusText}</span></td>
            </tr>
        `;
    });
    
    elements.attendanceTable.innerHTML = html;
}

// ===== LOAD SUMMARY STATS =====
async function loadSummaryStats() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/summary`);
        if (!response.ok) throw new Error('Failed to load summary');
        
        const data = await response.json();
        
        elements.statEntries.textContent = data.total_entries || 0;
        elements.statExits.textContent = data.total_exits || 0;
        elements.statPresent.textContent = data.present_count || 0;
    } catch (error) {
        console.error('❌ Failed to load summary:', error);
    }
}

// ===== AUTO REFRESH =====
function startAutoRefresh() {
    setInterval(async () => {
        if (!isProcessing) {
            await loadAttendanceData();
            await loadSummaryStats();
        }
    }, REFRESH_INTERVAL);
}

// ===== UTILITY FUNCTIONS =====
function formatDateTime(isoString) {
    if (!isoString) return '--';
    
    const date = new Date(isoString);
    const today = new Date();
    
    const timeStr = date.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: true
    });
    
    // If same day, just show time
    if (date.toDateString() === today.toDateString()) {
        return timeStr;
    }
    
    // Otherwise show date and time
    const dateStr = date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric'
    });
    
    return `${dateStr} ${timeStr}`;
}

// ===== CLEANUP =====
window.addEventListener('beforeunload', () => {
    if (cameraStream) {
        cameraStream.getTracks().forEach(track => track.stop());
    }
});

console.log('📱 SmartVision AI Attendance System loaded');
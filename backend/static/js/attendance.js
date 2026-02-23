// ===== CONFIGURATION =====
const API_BASE_URL = '';
const REFRESH_INTERVAL = 5000;

// ===== STATE =====
let cameraStream = null;
let isCameraActive = false;
let isProcessing = false;
let selectedDate = '';
let dayOneDate = '';

// Keep backend device mode in sync with attendance camera state.
async function setDeviceMode(mode) {
    try {
        await fetch(`${API_BASE_URL}/set_mode/${encodeURIComponent(mode)}`);
    } catch (error) {
        console.error('Failed to set device mode:', error);
    }
}

// ===== DOM ELEMENTS =====
const elements = {
    webcam: document.getElementById('webcam'),
    canvas: document.getElementById('canvas'),
    placeholder: document.getElementById('webcam-placeholder'),
    toggleCamera: document.getElementById('toggle-camera'),
    captureBtn: document.getElementById('capture-btn'),
    captureText: document.getElementById('capture-text'),
    captureSpinner: document.getElementById('capture-spinner'),
    resultSection: document.getElementById('result-section'),
    resultContent: document.getElementById('result-content'),
    attendanceTable: document.getElementById('attendance-table'),
    refreshBtn: document.getElementById('refresh-btn'),
    day1Btn: document.getElementById('day1-btn'),
    day2Btn: document.getElementById('day2-btn'),
    attendanceDate: document.getElementById('attendance-date'),
    setDateBtn: document.getElementById('set-date-btn'),
    selectedDateLabel: document.getElementById('selected-date-label'),
    statEntries: document.getElementById('stat-entries'),
    statExits: document.getElementById('stat-exits'),
    statPresent: document.getElementById('stat-present'),
    backendStatus: document.getElementById('backend-status'),
    backendUrl: document.getElementById('backend-url'),
    activeDateBadge: document.getElementById('active-date-badge')
};

document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
});

async function initializeApp() {
    elements.backendUrl.textContent = window.location.origin;
    await checkBackendConnection();
    setupEventListeners();
    await loadAttendanceData(true);
    await loadSummaryStats();
    startAutoRefresh();
}

function setupEventListeners() {
    elements.toggleCamera.addEventListener('click', toggleCamera);
    elements.captureBtn.addEventListener('click', captureAndRecognize);
    elements.refreshBtn.addEventListener('click', async () => {
        await loadAttendanceData();
        await loadSummaryStats();
    });
    elements.setDateBtn.addEventListener('click', async () => {
        const value = elements.attendanceDate.value;
        if (!value) return;
        await setAttendanceDate(value);
    });
    elements.day1Btn.addEventListener('click', async () => {
        const base = dayOneDate || selectedDate || getTodayIsoDate();
        dayOneDate = base;
        await setAttendanceDate(base, false);
    });
    elements.day2Btn.addEventListener('click', async () => {
        const base = dayOneDate || selectedDate || getTodayIsoDate();
        dayOneDate = base;
        await setAttendanceDate(addDays(base, 1), false);
    });
}

async function setAttendanceDate(targetDate, syncWithServer = true) {
    try {
        if (syncWithServer) {
            const response = await fetch(`${API_BASE_URL}/api/set-date`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ date: targetDate })
            });
            if (!response.ok) {
                throw new Error('Failed to set date');
            }
        }

        selectedDate = targetDate;
        if (!dayOneDate) {
            dayOneDate = targetDate;
        }

        updateDateControls();
        await loadAttendanceData();
        await loadSummaryStats();
    } catch (error) {
        showError('Failed to set attendance date.');
    }
}

async function checkBackendConnection() {
    try {
        const response = await fetch(`${API_BASE_URL}/`);
        if (response.ok) {
            updateBackendStatus(true);
            return true;
        }
    } catch (error) {
        console.error(error);
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

async function toggleCamera() {
    if (isCameraActive) {
        stopCamera();
    } else {
        await startCamera();
    }
}

async function startCamera() {
    try {
        await setDeviceMode('attendance');
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
    } catch (error) {
        await setDeviceMode('idle');
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
        setDeviceMode('idle');
    }
}

async function captureAndRecognize() {
    if (isProcessing || !isCameraActive) return;

    isProcessing = true;
    elements.captureBtn.disabled = true;
    elements.captureText.style.display = 'none';
    elements.captureSpinner.style.display = 'block';

    try {
        const imageBlob = await captureFrame();
        const result = await recognizeFace(imageBlob);
        displayResult(result);
        await loadAttendanceData();
        await loadSummaryStats();
    } catch (error) {
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

function displayResult(result) {
    const status = result.status;
    let html = '';

    if (status === 'entry' || status === 'exit') {
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
        html = `
            <div class="result-icon">⏱️</div>
            <div class="result-name">${result.name}</div>
            <span class="result-status entry">Cooldown Active</span>
            <p class="result-confidence">${result.message}</p>
        `;
    } else if (status === 'unknown' || status === 'unregistered') {
        html = `
            <div class="result-icon">❓</div>
            <div class="result-name">Unknown Person</div>
            <span class="result-status unknown">Not Recognized</span>
            <p class="result-confidence">No matching face found in database</p>
        `;
    } else if (status === 'no_face') {
        html = `
            <div class="result-icon">🔍</div>
            <div class="result-name">No Face Detected</div>
            <span class="result-status no_face">No Face</span>
            <p class="result-confidence">Please ensure your face is visible</p>
        `;
    } else {
        html = `
            <div class="result-icon">⚠️</div>
            <div class="result-name">Error</div>
            <span class="result-status unknown">Recognition Failed</span>
            <p class="result-confidence">${result.message || 'An error occurred'}</p>
        `;
    }

    elements.resultContent.innerHTML = html;
    elements.resultSection.style.display = 'block';

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

async function loadAttendanceData(syncFromServer = false) {
    try {
        const query = selectedDate ? `?date=${selectedDate}` : '';
        const response = await fetch(`${API_BASE_URL}/api/attendance${query}`);
        if (!response.ok) throw new Error('Failed to load attendance');

        const data = await response.json();

        if (data.date && (!selectedDate || syncFromServer)) {
            selectedDate = data.date;
            if (!dayOneDate) {
                dayOneDate = selectedDate;
            }
        }

        updateDateControls();
        renderAttendanceTable(data.records);
    } catch (error) {
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

async function loadSummaryStats() {
    try {
        const query = selectedDate ? `?date=${selectedDate}` : '';
        const response = await fetch(`${API_BASE_URL}/api/summary${query}`);
        if (!response.ok) throw new Error('Failed to load summary');

        const data = await response.json();

        elements.statEntries.textContent = data.total_entries || 0;
        elements.statExits.textContent = data.total_exits || 0;
        elements.statPresent.textContent = data.present_count || 0;
    } catch (error) {
        console.error(error);
    }
}

function updateDateControls() {
    const activeDate = selectedDate || getTodayIsoDate();
    elements.attendanceDate.value = activeDate;
    elements.selectedDateLabel.textContent = `Selected Date: ${formatDisplayDate(activeDate)}`;
    elements.activeDateBadge.textContent = `📅 Active Date: ${formatDisplayDate(activeDate)}`;

    if (!dayOneDate) {
        dayOneDate = activeDate;
    }

    const dayTwoDate = addDays(dayOneDate, 1);
    elements.day1Btn.classList.toggle('active', activeDate === dayOneDate);
    elements.day2Btn.classList.toggle('active', activeDate === dayTwoDate);
}

function getTodayIsoDate() {
    return new Date().toISOString().split('T')[0];
}

function addDays(isoDate, days) {
    const date = new Date(`${isoDate}T00:00:00`);
    date.setDate(date.getDate() + days);
    return date.toISOString().split('T')[0];
}

function formatDisplayDate(isoDate) {
    const date = new Date(`${isoDate}T00:00:00`);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

function startAutoRefresh() {
    setInterval(async () => {
        if (!isProcessing) {
            await loadAttendanceData();
            await loadSummaryStats();
        }
    }, REFRESH_INTERVAL);
}

function formatDateTime(isoString) {
    if (!isoString) return '--';

    const date = new Date(isoString);
    const today = new Date();

    const timeStr = date.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: true
    });

    if (date.toDateString() === today.toDateString()) {
        return timeStr;
    }

    const dateStr = date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric'
    });

    return `${dateStr} ${timeStr}`;
}

window.addEventListener('beforeunload', () => {
    if (cameraStream) {
        cameraStream.getTracks().forEach(track => track.stop());
    }
});

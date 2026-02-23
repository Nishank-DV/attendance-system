const API_BASE_URL = '';
const REFRESH_INTERVAL = 5000;
const LIVE_RESULT_POLL_INTERVAL = 1500;

let selectedDate = '';
let dayOneDate = '';
let lastResultKey = '';

const elements = {
    streamImage: document.getElementById('esp32-stream'),
    streamHealth: document.getElementById('stream-health'),
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
    await setDeviceMode('attendance');
    setupEventListeners();
    await loadAttendanceData(true);
    await loadSummaryStats();
    await refreshStreamStatus();
    startAutoRefresh();
    startLiveResultPolling();
}

function setupEventListeners() {
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

    if (elements.streamImage) {
        elements.streamImage.addEventListener('error', () => {
            updateStreamHealth('ESP32 stream unavailable. Waiting for reconnect...', false);
        });
        elements.streamImage.addEventListener('load', () => {
            updateStreamHealth('ESP32 stream active.', true);
        });
    }

    window.addEventListener('beforeunload', () => {
        setDeviceMode('idle');
    });
}

async function setDeviceMode(mode) {
    try {
        await fetch(`${API_BASE_URL}/set_mode/${encodeURIComponent(mode)}`);
    } catch (error) {
        console.error('Failed to set device mode:', error);
    }
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
        const response = await fetch(`${API_BASE_URL}/health`);
        updateBackendStatus(response.ok);
        return response.ok;
    } catch (error) {
        updateBackendStatus(false);
        return false;
    }
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

function updateStreamHealth(message, connected) {
    elements.streamHealth.textContent = message;
    elements.streamHealth.classList.remove('form-error', 'form-success');
    if (connected) {
        elements.streamHealth.classList.add('form-success');
    } else {
        elements.streamHealth.classList.add('form-error');
    }
}

async function refreshStreamStatus() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/stream-status`);
        if (!response.ok) {
            return;
        }

        const status = await response.json();
        if (status.connected) {
            updateStreamHealth('ESP32 stream active.', true);
            return;
        }

        updateStreamHealth(status.message || 'ESP32 stream disconnected.', false);
    } catch (error) {
        updateStreamHealth('Unable to fetch stream status.', false);
    }
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

async function pollLiveResult() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/live-result`);
        if (!response.ok) return;

        const result = await response.json();
        const stream = result.stream || {};
        if (stream.connected) {
            updateStreamHealth('ESP32 stream active.', true);
        } else {
            updateStreamHealth('ESP32 stream disconnected.', false);
        }

        if (result.status === 'waiting_frame' || result.status === 'skipped') {
            return;
        }

        const dedupeKey = `${result.updated_at || ''}|${result.status || ''}|${result.attendance_status || ''}|${result.name || ''}`;
        if (!dedupeKey || dedupeKey === lastResultKey) {
            return;
        }

        lastResultKey = dedupeKey;
        displayResult(result);
        await loadAttendanceData();
        await loadSummaryStats();
    } catch (error) {
        console.error('Live result poll failed:', error);
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

function displayResult(result) {
    const status = result.status;
    const attendanceStatus = result.attendance_status || status;
    let html = '';

    if (status === 'present' && (attendanceStatus === 'entry' || attendanceStatus === 'exit')) {
        const icon = attendanceStatus === 'entry' ? '✅' : '🚪';
        const statusText = attendanceStatus.charAt(0).toUpperCase() + attendanceStatus.slice(1);
        html = `
            <div class="result-icon">${icon}</div>
            <div class="result-name">${result.name}</div>
            <span class="result-status ${attendanceStatus}">${statusText} Recorded</span>
            <p class="result-confidence">Confidence: ${result.confidence || 0}%</p>
            <div class="confidence-bar">
                <div class="confidence-fill" style="width: ${result.confidence || 0}%"></div>
            </div>
        `;
    } else if (status === 'present' && attendanceStatus === 'cooldown') {
        html = `
            <div class="result-icon">⏱️</div>
            <div class="result-name">${result.name || 'Known Student'}</div>
            <span class="result-status entry">Cooldown Active</span>
            <p class="result-confidence">${result.message || 'Duplicate mark avoided.'}</p>
        `;
    } else if (status === 'unknown') {
        html = `
            <div class="result-icon">❓</div>
            <div class="result-name">Unknown Person</div>
            <span class="result-status unknown">Not Recognized</span>
            <p class="result-confidence">No matching face found in database</p>
        `;
    } else if (status === 'multiple_faces') {
        html = `
            <div class="result-icon">👥</div>
            <div class="result-name">Multiple Faces Detected</div>
            <span class="result-status unknown">Single Face Needed</span>
            <p class="result-confidence">Please keep only one face in frame</p>
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
            <div class="result-name">Recognition Error</div>
            <span class="result-status unknown">Failed</span>
            <p class="result-confidence">${result.message || 'An unexpected error occurred'}</p>
        `;
    }

    elements.resultContent.innerHTML = html;
    elements.resultSection.style.display = 'block';
    setTimeout(() => {
        elements.resultSection.style.display = 'none';
    }, 9000);
}

function showError(message) {
    elements.resultContent.innerHTML = `
        <div class="result-icon">⚠️</div>
        <div class="result-name">Error</div>
        <span class="result-status unknown">Failed</span>
        <p class="result-confidence">${message}</p>
    `;
    elements.resultSection.style.display = 'block';
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
        await loadAttendanceData();
        await loadSummaryStats();
        await refreshStreamStatus();
    }, REFRESH_INTERVAL);
}

function startLiveResultPolling() {
    setInterval(async () => {
        await pollLiveResult();
    }, LIVE_RESULT_POLL_INTERVAL);
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

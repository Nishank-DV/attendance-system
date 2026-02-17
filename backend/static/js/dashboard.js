const API_BASE_URL = '';

const elements = {
    attendanceDate: document.getElementById('attendance-date'),
    setDateBtn: document.getElementById('set-date-btn'),
    dateMsg: document.getElementById('date-msg'),
    startRegCamera: document.getElementById('start-reg-camera'),
    registerStudentBtn: document.getElementById('register-student'),
    regVideo: document.getElementById('reg-video'),
    regCanvas: document.getElementById('reg-canvas'),
    regMsg: document.getElementById('reg-msg'),
    name: document.getElementById('name'),
    rollNumber: document.getElementById('roll-number'),
    department: document.getElementById('department'),
    studentsTable: document.getElementById('students-table'),
    refreshStudents: document.getElementById('refresh-students')
};

let registrationStream = null;
let isCameraReady = false;

async function requestJson(url, options = {}) {
    const response = await fetch(url, options);
    const data = await response.json().catch(() => ({}));

    if (response.status === 401) {
        window.location.href = '/faculty';
        throw new Error('Unauthorized');
    }

    if (!response.ok) {
        throw new Error(data.message || `Request failed (${response.status})`);
    }

    return data;
}

async function setDate() {
    elements.dateMsg.textContent = '';
    try {
        await requestJson(`${API_BASE_URL}/api/set-date`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ date: elements.attendanceDate.value })
        });
        elements.dateMsg.textContent = `Selected Date: ${elements.attendanceDate.value}`;
    } catch (error) {
        elements.dateMsg.textContent = error.message;
    }
}

async function startRegCamera() {
    if (registrationStream) return;

    elements.regMsg.textContent = '';

    if (!window.isSecureContext && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
        elements.regMsg.textContent = 'Camera requires HTTPS or localhost. Open via http://127.0.0.1:5000.';
        return;
    }

    const getUserMedia = getUserMediaCompat();
    if (!getUserMedia) {
        elements.regMsg.textContent = 'Camera access is not supported in this browser. Try Chrome or Edge.';
        return;
    }

    try {
        registrationStream = await getUserMedia({
            video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'user' }
        });

        elements.regVideo.muted = true;
        elements.regVideo.srcObject = registrationStream;
        await waitForVideoReady(elements.regVideo);
        elements.registerStudentBtn.disabled = false;
        isCameraReady = true;
    } catch (error) {
        elements.regMsg.textContent = 'Failed to access camera. Please allow permission.';
    }
}

function getUserMediaCompat() {
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        return navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
    }

    const legacyGetUserMedia = navigator.getUserMedia || navigator.webkitGetUserMedia || navigator.mozGetUserMedia;
    if (!legacyGetUserMedia) {
        return null;
    }

    return (constraints) => new Promise((resolve, reject) => {
        legacyGetUserMedia.call(navigator, constraints, resolve, reject);
    });
}

function stopRegCamera() {
    if (!registrationStream) return;

    registrationStream.getTracks().forEach(track => track.stop());
    elements.regVideo.srcObject = null;
    registrationStream = null;
    elements.registerStudentBtn.disabled = true;
    isCameraReady = false;
}

async function captureRegistrationImage() {
    const video = elements.regVideo;
    await waitForVideoReady(video);
    if (!isCameraReady || !video.videoWidth || !video.videoHeight) {
        throw new Error('Camera is not ready.');
    }

    const canvas = elements.regCanvas;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0);

    return new Promise((resolve, reject) => {
        canvas.toBlob(blob => {
            if (!blob) {
                reject(new Error('Failed to capture image.'));
                return;
            }
            resolve(blob);
        }, 'image/jpeg', 0.95);
    });
}

function waitForVideoReady(video) {
    if (video.readyState >= 4) {
        isCameraReady = true;
        return Promise.resolve();
    }

    return new Promise((resolve, reject) => {
        const timeoutId = setTimeout(() => {
            reject(new Error('Camera is not ready.'));
        }, 3000);

        video.onloadedmetadata = () => {
            clearTimeout(timeoutId);
            isCameraReady = true;
            resolve();
        };
    });
}

async function registerStudent() {
    setRegMessage('', '');

    try {
        const imageBase64 = await captureRegistrationBase64();

        const payload = {
            name: elements.name.value.trim(),
            roll_number: elements.rollNumber.value.trim(),
            department: elements.department.value.trim(),
            image_base64: imageBase64
        };

        const response = await fetch(`${API_BASE_URL}/api/register-student`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await response.json().catch(() => ({}));

        if (!response.ok) {
            throw new Error(data.message || 'Registration failed.');
        }

        if (data.status === 'no_face') {
            setRegMessage('No face detected. Please try again.', 'error');
            return;
        }

        if (data.status !== 'registered') {
            throw new Error(data.message || 'Registration failed.');
        }

        setRegMessage('Registered successfully.', 'success');
        elements.name.value = '';
        elements.rollNumber.value = '';
        elements.department.value = '';
        await loadStudents();
    } catch (error) {
        setRegMessage(error.message, 'error');
    }
}

async function captureRegistrationBase64() {
    const video = elements.regVideo;
    await waitForVideoReady(video);
    if (!isCameraReady || !video.videoWidth || !video.videoHeight) {
        throw new Error('Camera is not ready.');
    }

    const canvas = elements.regCanvas;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0);

    return canvas.toDataURL('image/jpeg', 0.95);
}

function setRegMessage(message, type) {
    elements.regMsg.textContent = message;
    elements.regMsg.classList.remove('form-error', 'form-success');
    if (type === 'error') {
        elements.regMsg.classList.add('form-error');
    }
    if (type === 'success') {
        elements.regMsg.classList.add('form-success');
    }
}

async function deleteStudent(studentId) {
    await requestJson(`${API_BASE_URL}/api/delete-student`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: studentId })
    });
    await loadStudents();
}

async function loadStudents() {
    try {
        const data = await requestJson(`${API_BASE_URL}/api/students`);
        const students = data.students || [];

        if (students.length === 0) {
            elements.studentsTable.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:20px;">No students registered</td></tr>';
            return;
        }

        elements.studentsTable.innerHTML = students
            .map(student => `
                <tr>
                    <td>${student.id}</td>
                    <td>${student.name}</td>
                    <td>${student.roll_number}</td>
                    <td>${student.department}</td>
                    <td><button class="btn-secondary" data-student-id="${student.id}">Delete</button></td>
                </tr>
            `)
            .join('');

        elements.studentsTable.querySelectorAll('button[data-student-id]').forEach(button => {
            button.addEventListener('click', async () => {
                await deleteStudent(parseInt(button.dataset.studentId, 10));
            });
        });
    } catch (error) {
        elements.studentsTable.innerHTML = `<tr><td colspan="5" style="text-align:center;color:#d32f2f;padding:20px;">${error.message}</td></tr>`;
    }
}

function setupEvents() {
    elements.setDateBtn.addEventListener('click', setDate);
    elements.startRegCamera.addEventListener('click', startRegCamera);
    elements.registerStudentBtn.addEventListener('click', registerStudent);
    elements.refreshStudents.addEventListener('click', loadStudents);
    window.addEventListener('beforeunload', stopRegCamera);
}

function setDefaultDate() {
    const today = new Date().toISOString().split('T')[0];
    elements.attendanceDate.value = today;
    elements.dateMsg.textContent = `Selected Date: ${today}`;
}

setupEvents();
setDefaultDate();
loadStudents();
elements.registerStudentBtn.disabled = true;

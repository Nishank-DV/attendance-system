const API_BASE_URL = '';

const elements = {
    attendanceDate: document.getElementById('attendance-date'),
    setDateBtn: document.getElementById('set-date-btn'),
    dateMsg: document.getElementById('date-msg'),
    registerStudentBtn: document.getElementById('register-student'),
    regStream: document.getElementById('reg-stream'),
    regMsg: document.getElementById('reg-msg'),
    name: document.getElementById('name'),
    rollNumber: document.getElementById('roll-number'),
    department: document.getElementById('department'),
    studentsTable: document.getElementById('students-table'),
    refreshStudents: document.getElementById('refresh-students')
};

// Keep backend device mode in sync with dashboard actions.
async function setDeviceMode(mode) {
    try {
        await fetch(`${API_BASE_URL}/set_mode/${encodeURIComponent(mode)}`);
    } catch (error) {
        console.error('Failed to set device mode:', error);
    }
}

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

async function captureRegistrationBase64() {
    const response = await fetch(`${API_BASE_URL}/api/latest-frame`, {
        method: 'GET'
    });

    if (!response.ok) {
        throw new Error('No ESP32 frame available. Check stream connection.');
    }

    const blob = await response.blob();
    const arrayBuffer = await blob.arrayBuffer();
    const bytes = new Uint8Array(arrayBuffer);

    let binary = '';
    const chunkSize = 0x8000;
    for (let i = 0; i < bytes.length; i += chunkSize) {
        const chunk = bytes.subarray(i, i + chunkSize);
        binary += String.fromCharCode.apply(null, chunk);
    }

    return `data:image/jpeg;base64,${btoa(binary)}`;
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
    elements.registerStudentBtn.addEventListener('click', registerStudent);
    elements.refreshStudents.addEventListener('click', loadStudents);
    if (elements.regStream) {
        elements.regStream.addEventListener('error', () => setRegMessage('ESP32 stream unavailable.', 'error'));
        elements.regStream.addEventListener('load', () => setRegMessage('', ''));
    }
    window.addEventListener('beforeunload', () => setDeviceMode('idle'));
}

function setDefaultDate() {
    const today = new Date().toISOString().split('T')[0];
    elements.attendanceDate.value = today;
    elements.dateMsg.textContent = `Selected Date: ${today}`;
}

setupEvents();
setDefaultDate();
loadStudents();
setDeviceMode('register');

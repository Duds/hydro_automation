// API base URL
const API_BASE = '/api';

// Polling interval (milliseconds)
const POLL_INTERVAL = 3000; // 3 seconds

// State
let statusPollInterval = null;
let logsPollInterval = null;
let cycles = [];

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initializeUI();
    startPolling();
    setupEventListeners();
});

function initializeUI() {
    // Setup main tab switching
    const mainTabButtons = document.querySelectorAll('.main-tab-btn');
    mainTabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabName = btn.dataset.tab;
            switchMainTab(tabName);
        });
    });

    // Load initial configuration
    loadScheduleConfig();
}

function switchMainTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.main-tab-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.tab === tabName) {
            btn.classList.add('active');
        }
    });

    // Update tab content
    document.querySelectorAll('.main-tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`${tabName}Tab`).classList.add('active');
}

function setupEventListeners() {
    // Control buttons
    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');
    const deviceOnBtn = document.getElementById('deviceOnBtn');
    const deviceOffBtn = document.getElementById('deviceOffBtn');
    const emergencyStopBtn = document.getElementById('emergencyStopBtn');

    if (startBtn) startBtn.addEventListener('click', startScheduler);
    if (stopBtn) stopBtn.addEventListener('click', stopScheduler);
    if (deviceOnBtn) deviceOnBtn.addEventListener('click', turnDeviceOn);
    if (deviceOffBtn) deviceOffBtn.addEventListener('click', turnDeviceOff);
    if (emergencyStopBtn) emergencyStopBtn.addEventListener('click', emergencyStop);

    // Schedule configuration buttons
    const addCycleBtn = document.getElementById('addCycleBtn');
    const saveScheduleConfigBtn = document.getElementById('saveScheduleConfig');
    const refreshLogsBtn = document.getElementById('refreshLogs');

    if (addCycleBtn) addCycleBtn.addEventListener('click', addCycle);
    if (saveScheduleConfigBtn) saveScheduleConfigBtn.addEventListener('click', saveScheduleConfig);
    if (refreshLogsBtn) refreshLogsBtn.addEventListener('click', loadLogs);

    // Settings buttons
    const saveSettingsBtn = document.getElementById('saveSettings');
    if (saveSettingsBtn) saveSettingsBtn.addEventListener('click', saveSettings);

    const scheduleTypeSelect = document.getElementById('scheduleTypeSelect');
    if (scheduleTypeSelect) {
        scheduleTypeSelect.addEventListener('change', (e) => {
            toggleSettingsVisibility(e.target.value);
        });
    }

    // Auto-scroll checkbox
    const autoScrollCheckbox = document.getElementById('autoScroll');
    if (autoScrollCheckbox) {
        autoScrollCheckbox.addEventListener('change', (e) => {
            if (e.target.checked) {
                scrollLogsToBottom();
            }
        });
    }
}

function startPolling() {
    // Poll status every 3 seconds
    statusPollInterval = setInterval(updateStatus, POLL_INTERVAL);

    // Poll logs every 5 seconds
    logsPollInterval = setInterval(loadLogs, 5000);

    // Initial load
    updateStatus();
    loadLogs();
}

async function updateStatus() {
    try {
        const response = await fetch(`${API_BASE}/status`);
        if (!response.ok) throw new Error('Status fetch failed');
        const status = await response.json();
        updateStatusUI(status);
    } catch (error) {
        console.error('Error fetching status:', error);
        updateStatusIndicator(false, 'Connection Error');
    }
}

function updateStatusUI(status) {
    const isConnected = status.controller_running && status.device_connected;
    updateStatusIndicator(isConnected, isConnected ? 'Connected' : 'Disconnected');

    document.getElementById('controllerStatus').textContent = status.controller_running ? 'Running' : 'Stopped';
    document.getElementById('schedulerStatus').textContent = status.scheduler_running ? 'Running' : 'Stopped';

    const stateElement = document.getElementById('schedulerState');
    const state = status.scheduler_state || 'idle';
    stateElement.textContent = state.charAt(0).toUpperCase() + state.slice(1);
    stateElement.className = 'state-indicator ' + state;

    const nextEventElement = document.getElementById('nextEvent');
    if (status.next_event_time && status.next_event_time !== 'N/A') {
        const eventDate = new Date(status.next_event_time);
        nextEventElement.textContent = isNaN(eventDate.getTime()) ? status.next_event_time : eventDate.toLocaleTimeString();
    } else {
        nextEventElement.textContent = 'N/A';
    }

    document.getElementById('timeUntilNextCycle').textContent = status.time_until_next_cycle || 'N/A';
    document.getElementById('deviceConnected').textContent = status.device_connected ? 'Connected' : 'Disconnected';

    const deviceState = status.device_state === null ? 'Unknown' : (status.device_state ? 'ON' : 'OFF');
    const deviceStateElement = document.getElementById('deviceState');
    deviceStateElement.textContent = deviceState;
    deviceStateElement.className = 'device-state-indicator ' + (status.device_state ? 'on' : 'off');

    document.getElementById('deviceIP').textContent = status.device_ip || 'N/A';
    document.getElementById('scheduleMode').textContent = status.scheduler_mode ? status.scheduler_mode.charAt(0).toUpperCase() + status.scheduler_mode.slice(1).replace('_', ' ') : 'N/A';

    document.getElementById('startBtn').disabled = status.scheduler_running;
    document.getElementById('stopBtn').disabled = !status.scheduler_running;
}

function updateStatusIndicator(connected, text) {
    const dot = document.getElementById('statusDot');
    const textEl = document.getElementById('statusText');
    if (dot) dot.classList.toggle('connected', connected);
    if (textEl) textEl.textContent = text;
}

async function loadLogs() {
    try {
        const response = await fetch(`${API_BASE}/logs?lines=100`);
        if (!response.ok) throw new Error('Logs fetch failed');
        const data = await response.json();
        displayLogs(data.logs);
    } catch (error) {
        console.error('Error loading logs:', error);
    }
}

function displayLogs(logs) {
    const logsContent = document.getElementById('logsContent');
    if (!logsContent) return;
    const autoScroll = document.getElementById('autoScroll').checked;

    logsContent.innerHTML = logs.map(log => {
        let className = '';
        if (log.includes('ERROR')) className = 'log-error';
        else if (log.includes('WARNING')) className = 'log-warning';
        else if (log.includes('INFO')) className = 'log-info';
        return `<span class="${className}">${escapeHtml(log)}</span>`;
    }).join('\n');

    if (autoScroll) scrollLogsToBottom();
}

function scrollLogsToBottom() {
    const container = document.querySelector('.logs-container');
    if (container) container.scrollTop = container.scrollHeight;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

async function startScheduler() {
    try {
        const response = await fetch(`${API_BASE}/control/start`, { method: 'POST' });
        const result = await response.json();
        if (result.success) showMessage('Scheduler started', 'success');
        else showMessage(result.message, 'error');
        updateStatus();
    } catch (error) {
        showMessage('Error: ' + error.message, 'error');
    }
}

async function stopScheduler() {
    try {
        const response = await fetch(`${API_BASE}/control/stop`, { method: 'POST' });
        const result = await response.json();
        if (result.success) showMessage('Scheduler stopped', 'success');
        else showMessage(result.message, 'error');
        updateStatus();
    } catch (error) {
        showMessage('Error: ' + error.message, 'error');
    }
}

async function turnDeviceOn() {
    try {
        const response = await fetch(`${API_BASE}/device/on`, { method: 'POST' });
        const result = await response.json();
        if (result.success) showMessage('Device turned ON', 'success');
        else showMessage(result.message, 'error');
        updateStatus();
    } catch (error) {
        showMessage('Error: ' + error.message, 'error');
    }
}

async function turnDeviceOff() {
    try {
        const response = await fetch(`${API_BASE}/device/off`, { method: 'POST' });
        const result = await response.json();
        if (result.success) showMessage('Device turned OFF', 'success');
        else showMessage(result.message, 'error');
        updateStatus();
    } catch (error) {
        showMessage('Error: ' + error.message, 'error');
    }
}

async function emergencyStop() {
    if (!confirm('Execute Emergency Stop? (Turn off device and stop scheduler)')) return;
    try {
        await turnDeviceOff();
        await stopScheduler();
        showMessage('Emergency stop executed', 'success');
    } catch (error) {
        showMessage('Error: ' + error.message, 'error');
    }
}

async function loadScheduleConfig() {
    try {
        const response = await fetch(`${API_BASE}/config/schedule`);
        const config = await response.json();
        document.getElementById('scheduleType').textContent = config.type || 'interval';
        cycles = config.cycles || [];
        renderCyclesTable();

        // Populate Settings Tab
        const scheduleTypeSelect = document.getElementById('scheduleTypeSelect');
        if (scheduleTypeSelect) {
            scheduleTypeSelect.value = config.type || 'interval';
            toggleSettingsVisibility(scheduleTypeSelect.value);
        }

        const floodDurationEl = document.getElementById('floodDuration');
        if (floodDurationEl) floodDurationEl.value = config.flood_duration_minutes || 2.0;

        const drainDurationEl = document.getElementById('drainDuration');
        if (drainDurationEl) drainDurationEl.value = config.drain_duration_minutes || 5.0;

        const intervalMinutesEl = document.getElementById('intervalMinutes');
        if (intervalMinutesEl) intervalMinutesEl.value = config.interval_minutes || 60;

        const startEl = document.getElementById('activeHoursStart');
        const endEl = document.getElementById('activeHoursEnd');
        if (startEl) startEl.value = config.active_hours_start || '';
        if (endEl) endEl.value = config.active_hours_end || '';
    } catch (error) {
        console.error('Error loading schedule:', error);
    }
}

function renderCyclesTable() {
    const tbody = document.getElementById('cyclesTableBody');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (cycles.length === 0) {
        tbody.innerHTML = '<tr><td colspan="3" style="text-align: center; padding: 20px; color: #666;">No cycles defined</td></tr>';
        return;
    }

    cycles.sort((a, b) => a.on_time.localeCompare(b.on_time));

    cycles.forEach((cycle, index) => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td><input type="time" class="cycle-on-time" value="${cycle.on_time}" data-index="${index}"></td>
            <td><input type="number" class="cycle-off-duration" value="${cycle.off_duration_minutes.toFixed(1)}" step="0.1" min="0" data-index="${index}"></td>
            <td><button class="btn btn-danger btn-small remove-cycle" data-index="${index}">Remove</button></td>
        `;
        tbody.appendChild(row);
    });

    document.querySelectorAll('.cycle-on-time').forEach(input => {
        input.addEventListener('change', (e) => cycles[e.target.dataset.index].on_time = e.target.value);
    });
    document.querySelectorAll('.cycle-off-duration').forEach(input => {
        input.addEventListener('change', (e) => cycles[e.target.dataset.index].off_duration_minutes = parseFloat(e.target.value) || 0);
    });
    document.querySelectorAll('.remove-cycle').forEach(btn => {
        btn.addEventListener('click', (e) => {
            cycles.splice(e.target.dataset.index, 1);
            renderCyclesTable();
        });
    });
}

function addCycle() {
    cycles.push({ on_time: '00:00', off_duration_minutes: 0 });
    renderCyclesTable();
}

async function saveScheduleConfig() {
    if (cycles.length === 0) return showMessage('At least one cycle must be defined', 'error');
    try {
        const response = await fetch(`${API_BASE}/config/schedule`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type: 'time_based', cycles: cycles })
        });
        const result = await response.json();
        if (result.success) showMessage(result.message, 'success');
        else showMessage(result.message, 'error');
    } catch (error) {
        showMessage('Error: ' + error.message, 'error');
    }
}

async function saveSettings() {
    try {
        const type = document.getElementById('scheduleTypeSelect').value;
        const schedule = { type: type };

        schedule.flood_duration_minutes = parseFloat(document.getElementById('floodDuration').value) || 2.0;

        if (type === 'interval') {
            schedule.drain_duration_minutes = parseFloat(document.getElementById('drainDuration').value) || 5.0;
            schedule.interval_minutes = parseFloat(document.getElementById('intervalMinutes').value) || 60.0;
            schedule.active_hours_start = document.getElementById('activeHoursStart').value || null;
            schedule.active_hours_end = document.getElementById('activeHoursEnd').value || null;
        } else {
            schedule.cycles = cycles;
        }

        const response = await fetch(`${API_BASE}/config/schedule`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(schedule)
        });

        const result = await response.json();
        if (response.ok) showMessage('Settings saved. Restart daemon to apply.', 'success');
        else showMessage(result.message || 'Error saving settings', 'error');
    } catch (error) {
        showMessage('Error: ' + error.message, 'error');
    }
}

function showMessage(message, type) {
    alert(message);
}

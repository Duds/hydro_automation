// API base URL
const API_BASE = '/api';

// Polling interval (milliseconds)
const POLL_INTERVAL = 3000; // 3 seconds

// State
let statusPollInterval = null;
let logsPollInterval = null;

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
    updateServiceStatus();
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
    document.getElementById('startBtn').addEventListener('click', startScheduler);
    document.getElementById('stopBtn').addEventListener('click', stopScheduler);
    document.getElementById('deviceOnBtn').addEventListener('click', turnDeviceOn);
    document.getElementById('deviceOffBtn').addEventListener('click', turnDeviceOff);
    document.getElementById('emergencyStopBtn').addEventListener('click', emergencyStop);

    // Schedule configuration buttons
    document.getElementById('addCycleBtn').addEventListener('click', addCycle);
    document.getElementById('saveScheduleConfig').addEventListener('click', saveScheduleConfig);
    document.getElementById('refreshLogs').addEventListener('click', loadLogs);

    // Service management buttons
    document.getElementById('daemonStartBtn').addEventListener('click', () => controlService('daemon', 'start'));
    document.getElementById('daemonStopBtn').addEventListener('click', () => controlService('daemon', 'stop'));
    document.getElementById('daemonRestartBtn').addEventListener('click', () => controlService('daemon', 'restart'));
    document.getElementById('webappStartBtn').addEventListener('click', () => controlService('webapp', 'start'));
    document.getElementById('webappStopBtn').addEventListener('click', () => controlService('webapp', 'stop'));
    document.getElementById('webappRestartBtn').addEventListener('click', () => controlService('webapp', 'restart'));

    // Auto-scroll checkbox
    document.getElementById('autoScroll').addEventListener('change', (e) => {
        if (e.target.checked) {
            scrollLogsToBottom();
        }
    });
}

function startPolling() {
    // Poll status every 3 seconds
    statusPollInterval = setInterval(updateStatus, POLL_INTERVAL);
    
    // Poll logs every 5 seconds
    logsPollInterval = setInterval(loadLogs, 5000);
    
    // Poll service status every 10 seconds
    setInterval(updateServiceStatus, 10000);
    
    // Poll environment data every 60 seconds
    setInterval(updateEnvironment, 60000);
    
    // Initial load
    updateStatus();
    loadLogs();
    updateServiceStatus();
    updateEnvironment();
}

function stopPolling() {
    if (statusPollInterval) {
        clearInterval(statusPollInterval);
        statusPollInterval = null;
    }
    if (logsPollInterval) {
        clearInterval(logsPollInterval);
        logsPollInterval = null;
    }
}

async function updateStatus() {
    try {
        const response = await fetch(`${API_BASE}/status`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const status = await response.json();
        updateStatusUI(status);
    } catch (error) {
        console.error('Error fetching status:', error);
        updateStatusIndicator(false, 'Connection Error');
    }
}

function updateStatusUI(status) {
    // Update status indicator
    const isConnected = status.controller_running && status.device_connected;
    updateStatusIndicator(isConnected, isConnected ? 'Connected' : 'Disconnected');

    // Update controller status
    document.getElementById('controllerStatus').textContent = 
        status.controller_running ? 'Running' : 'Stopped';
    
    // Update scheduler status
    document.getElementById('schedulerStatus').textContent = 
        status.scheduler_running ? 'Running' : 'Stopped';
    
    // Update scheduler state
    const state = status.scheduler_state || 'idle';
    document.getElementById('schedulerState').textContent = 
        state.charAt(0).toUpperCase() + state.slice(1);
    
    // Update next event
    document.getElementById('nextEvent').textContent = 
        status.next_event_time || 'N/A';

    // Update device status
    document.getElementById('deviceConnected').textContent = 
        status.device_connected ? 'Connected' : 'Disconnected';
    
    const deviceState = status.device_state === null ? 'Unknown' : 
                       status.device_state ? 'ON' : 'OFF';
    document.getElementById('deviceState').textContent = deviceState;
    
    document.getElementById('deviceIP').textContent = status.device_ip || 'N/A';

    // Update button states
    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');
    
    if (status.scheduler_running) {
        startBtn.disabled = true;
        stopBtn.disabled = false;
    } else {
        startBtn.disabled = false;
        stopBtn.disabled = true;
    }
}

function updateStatusIndicator(connected, text) {
    const dot = document.getElementById('statusDot');
    const textEl = document.getElementById('statusText');
    
    if (connected) {
        dot.classList.add('connected');
    } else {
        dot.classList.remove('connected');
    }
    textEl.textContent = text;
}

async function loadLogs() {
    try {
        const response = await fetch(`${API_BASE}/logs?lines=100`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        displayLogs(data.logs);
    } catch (error) {
        console.error('Error loading logs:', error);
        document.getElementById('logsContent').textContent = 'Error loading logs';
    }
}

function displayLogs(logs) {
    const logsContent = document.getElementById('logsContent');
    const autoScroll = document.getElementById('autoScroll').checked;
    
    // Format logs with color coding
    const formattedLogs = logs.map(log => {
        let className = '';
        if (log.includes('ERROR') || log.includes('CRITICAL')) {
            className = 'log-error';
        } else if (log.includes('WARNING')) {
            className = 'log-warning';
        } else if (log.includes('INFO')) {
            className = 'log-info';
        }
        return `<span class="${className}">${escapeHtml(log)}</span>`;
    }).join('\n');
    
    logsContent.innerHTML = formattedLogs;
    
    if (autoScroll) {
        scrollLogsToBottom();
    }
}

function scrollLogsToBottom() {
    const logsContainer = document.querySelector('.logs-container');
    logsContainer.scrollTop = logsContainer.scrollHeight;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

async function startScheduler() {
    try {
        const response = await fetch(`${API_BASE}/control/start`, {
            method: 'POST'
        });
        const result = await response.json();
        if (result.success) {
            showMessage('Scheduler started', 'success');
            updateStatus();
        } else {
            showMessage(result.message, 'error');
        }
    } catch (error) {
        showMessage('Error starting scheduler: ' + error.message, 'error');
    }
}

async function stopScheduler() {
    try {
        const response = await fetch(`${API_BASE}/control/stop`, {
            method: 'POST'
        });
        const result = await response.json();
        if (result.success) {
            showMessage('Scheduler stopped', 'success');
            updateStatus();
        } else {
            showMessage(result.message, 'error');
        }
    } catch (error) {
        showMessage('Error stopping scheduler: ' + error.message, 'error');
    }
}

async function turnDeviceOn() {
    try {
        const response = await fetch(`${API_BASE}/device/on`, {
            method: 'POST'
        });
        const result = await response.json();
        if (result.success) {
            showMessage('Device turned ON', 'success');
            updateStatus();
        } else {
            showMessage(result.message, 'error');
        }
    } catch (error) {
        showMessage('Error turning device on: ' + error.message, 'error');
    }
}

async function turnDeviceOff() {
    try {
        const response = await fetch(`${API_BASE}/device/off`, {
            method: 'POST'
        });
        const result = await response.json();
        if (result.success) {
            showMessage('Device turned OFF', 'success');
            updateStatus();
        } else {
            showMessage(result.message, 'error');
        }
    } catch (error) {
        showMessage('Error turning device off: ' + error.message, 'error');
    }
}

async function emergencyStop() {
    if (!confirm('Are you sure you want to perform an emergency stop? This will turn off the device immediately.')) {
        return;
    }
    
    try {
        // Turn device off and stop scheduler
        await turnDeviceOff();
        await stopScheduler();
        showMessage('Emergency stop executed', 'success');
    } catch (error) {
        showMessage('Error during emergency stop: ' + error.message, 'error');
    }
}

let cycles = [];

async function loadScheduleConfig() {
    try {
        const response = await fetch(`${API_BASE}/config/schedule`);
        const config = await response.json();
        
        document.getElementById('scheduleType').textContent = config.type || 'interval';
        
        // Load flood duration
        if (config.flood_duration_minutes) {
            document.getElementById('floodDuration').value = config.flood_duration_minutes;
        }
        
        // Load cycles
        if (config.cycles && Array.isArray(config.cycles)) {
            cycles = config.cycles;
        } else if (config.on_times && Array.isArray(config.on_times)) {
            // Convert legacy on_times to cycles format
            cycles = config.on_times.map(time => ({
                on_time: time,
                off_duration_minutes: 0  // Default, will wait until next scheduled time
            }));
        } else {
            cycles = [];
        }
        
        renderCyclesTable();
    } catch (error) {
        console.error('Error loading schedule config:', error);
    }
}

function renderCyclesTable() {
    const tbody = document.getElementById('cyclesTableBody');
    tbody.innerHTML = '';
    
    // Sort cycles by time
    cycles.sort((a, b) => {
        const timeA = parseTimeForSort(a.on_time);
        const timeB = parseTimeForSort(b.on_time);
        return timeA - timeB;
    });
    
    cycles.forEach((cycle, index) => {
        const row = document.createElement('tr');
        
        // Ensure time is in HH:MM format for time input
        let timeValue = cycle.on_time;
        if (timeValue && !timeValue.includes(':')) {
            // Handle formats like "0600" -> "06:00"
            if (timeValue.length === 4) {
                timeValue = timeValue.substring(0, 2) + ':' + timeValue.substring(2);
            }
        }
        
        row.innerHTML = `
            <td>
                <input type="time" class="cycle-on-time" value="${timeValue || '00:00'}" data-index="${index}">
            </td>
            <td>
                <input type="number" class="cycle-off-duration" value="${cycle.off_duration_minutes || 0}" 
                       step="0.1" min="0" data-index="${index}">
            </td>
            <td>
                <button class="btn btn-danger btn-small remove-cycle" data-index="${index}">Remove</button>
            </td>
        `;
        
        tbody.appendChild(row);
    });
    
    // Add event listeners
    document.querySelectorAll('.cycle-on-time').forEach(input => {
        input.addEventListener('change', (e) => {
            const index = parseInt(e.target.dataset.index);
            cycles[index].on_time = e.target.value;
        });
    });
    
    document.querySelectorAll('.cycle-off-duration').forEach(input => {
        input.addEventListener('change', (e) => {
            const index = parseInt(e.target.dataset.index);
            cycles[index].off_duration_minutes = parseFloat(e.target.value) || 0;
        });
    });
    
    document.querySelectorAll('.remove-cycle').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const index = parseInt(e.target.dataset.index);
            cycles.splice(index, 1);
            renderCyclesTable();
        });
    });
}

function parseTimeForSort(timeStr) {
    const parts = timeStr.split(':');
    return parseInt(parts[0]) * 60 + parseInt(parts[1]);
}

function addCycle() {
    // Add a new cycle with default values
    cycles.push({
        on_time: '00:00',
        off_duration_minutes: 0
    });
    renderCyclesTable();
}

async function saveScheduleConfig() {
    const floodDuration = parseFloat(document.getElementById('floodDuration').value);
    
    if (isNaN(floodDuration) || floodDuration <= 0) {
        showMessage('Flood duration must be a positive number', 'error');
        return;
    }
    
    if (cycles.length === 0) {
        showMessage('At least one cycle must be defined', 'error');
        return;
    }
    
    // Validate all cycles
    for (let i = 0; i < cycles.length; i++) {
        const cycle = cycles[i];
        if (!cycle.on_time) {
            showMessage(`Cycle ${i + 1} must have an ON time`, 'error');
            return;
        }
        if (cycle.off_duration_minutes < 0) {
            showMessage(`Cycle ${i + 1} OFF duration must be >= 0`, 'error');
            return;
        }
    }
    
    try {
        const response = await fetch(`${API_BASE}/config/schedule`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                type: 'time_based',
                flood_duration_minutes: floodDuration,
                cycles: cycles
            })
        });
        
        const result = await response.json();
        if (result.success) {
            showMessage(result.message, 'success');
        } else {
            showMessage(result.message, 'error');
        }
    } catch (error) {
        showMessage('Error saving schedule: ' + error.message, 'error');
    }
}

function showMessage(message, type) {
    // Simple alert for now - could be enhanced with a toast notification
    alert(message);
}

async function updateServiceStatus() {
    try {
        const response = await fetch(`${API_BASE}/service/status`);
        if (response.ok) {
            const status = await response.json();
            document.getElementById('daemonStatus').textContent = status.daemon_running ? 'Running' : 'Stopped';
            document.getElementById('webappStatus').textContent = status.webapp_running ? 'Running' : 'Stopped';
        }
    } catch (error) {
        console.error('Error fetching service status:', error);
    }
}

async function controlService(service, action) {
    try {
        const response = await fetch(`${API_BASE}/service/${service}/${action}`, {
            method: 'POST'
        });
        const result = await response.json();
        if (result.success) {
            showMessage(result.message, 'success');
            // Update status after a short delay
            setTimeout(updateServiceStatus, 1000);
        } else {
            showMessage(result.message, 'error');
        }
    } catch (error) {
        showMessage(`Error ${action}ing ${service}: ${error.message}`, 'error');
    }
}

async function updateEnvironment() {
    try {
        const response = await fetch(`${API_BASE}/environment`);
        if (response.ok) {
            const env = await response.json();
            
            // Update temperature
            if (env.temperature !== null && env.temperature !== undefined) {
                document.getElementById('temperature').textContent = `${env.temperature}°C`;
            } else {
                document.getElementById('temperature').textContent = 'N/A';
            }
            
            // Update sunrise/sunset
            document.getElementById('sunrise').textContent = env.sunrise || 'N/A';
            document.getElementById('sunset').textContent = env.sunset || 'N/A';
            
            // Update adaptation status
            document.getElementById('adaptationStatus').textContent = 
                env.adaptation_enabled ? 'Enabled' : 'Disabled';
        }
    } catch (error) {
        console.error('Error fetching environment data:', error);
    }
}


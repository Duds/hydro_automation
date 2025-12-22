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

        // Settings buttons
        document.getElementById('saveSettings').addEventListener('click', saveSettings);
        document.getElementById('resetSettings').addEventListener('click', resetSettings);

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
    loadSettings();
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
        // For restart, the server may go down temporarily, so handle it specially
        if (action === 'restart' && service === 'daemon') {
            showMessage('Restarting daemon... (this may take a few seconds)', 'success');
            
            // Send restart request with a timeout
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 2000); // 2 second timeout
            
            try {
                const response = await fetch(`${API_BASE}/service/${service}/${action}`, {
                    method: 'POST',
                    signal: controller.signal
                });
                clearTimeout(timeoutId);
                const result = await response.json();
                if (result.success) {
                    showMessage(result.message, 'success');
                } else {
                    showMessage(result.message, 'error');
                }
            } catch (fetchError) {
                clearTimeout(timeoutId);
                // If fetch fails (network error), the server likely went down during restart
                // This is expected - wait and check if it comes back
                showMessage('Daemon restart initiated. Waiting for service to come back online...', 'success');
                
                // Poll for service to come back online
                let attempts = 0;
                const maxAttempts = 15; // 15 attempts = ~15 seconds
                const pollInterval = setInterval(async () => {
                    attempts++;
                    try {
                        const statusResponse = await fetch(`${API_BASE}/service/status`);
                        if (statusResponse.ok) {
                            const status = await statusResponse.json();
                            clearInterval(pollInterval);
                            if (status.daemon_running) {
                                showMessage('Daemon restarted successfully!', 'success');
                                updateServiceStatus();
                            } else {
                                showMessage('Daemon restart may have failed. Please check status.', 'error');
                                updateServiceStatus();
                            }
                        }
                    } catch (pollError) {
                        // Still waiting for server to come back
                        if (attempts >= maxAttempts) {
                            clearInterval(pollInterval);
                            showMessage('Daemon restart timed out. Please check if the daemon is running manually.', 'error');
                            updateServiceStatus();
                        }
                    }
                }, 1000); // Poll every second
            }
        } else {
            // For start/stop, normal handling
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
        }
    } catch (error) {
        // Only show error if it's not a network error during restart
        if (!(action === 'restart' && service === 'daemon' && error.name === 'AbortError')) {
            showMessage(`Error ${action}ing ${service}: ${error.message}`, 'error');
        }
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
            
            // Update station name
            if (env.temperature_station_name) {
                document.getElementById('temperatureStationName').textContent = 
                    `${env.temperature_station_name} (${env.temperature_station_id})`;
            } else if (env.temperature_station_id) {
                document.getElementById('temperatureStationName').textContent = 
                    `Station ${env.temperature_station_id}`;
            } else {
                document.getElementById('temperatureStationName').textContent = 'N/A';
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

async function loadSettings() {
    try {
        const response = await fetch(`${API_BASE}/config/schedule`);
        if (response.ok) {
            const schedule = await response.json();
            const adaptation = schedule.adaptation || {};
            const location = adaptation.location || {};
            const temperature = adaptation.temperature || {};
            const daylight = adaptation.daylight || {};

            // Location settings
            document.getElementById('postcode').value = location.postcode || '';
            document.getElementById('timezone').value = location.timezone || 'Australia/Sydney';

            // Temperature settings
            document.getElementById('temperatureEnabled').checked = temperature.enabled || false;
            const stationId = temperature.station_id;
            // Display station name if we have a station ID
            if (stationId && stationId !== 'auto') {
                // Fetch station name to display
                fetch(`${API_BASE}/bom/stations/${stationId}`)
                    .then(r => r.json())
                    .then(station => {
                        const stationInput = document.getElementById('temperatureStation');
                        if (stationInput) {
                            stationInput.value = `${station.name} (${station.id})`;
                        }
                    })
                    .catch(() => {
                        // If fetch fails, just show the ID
                        const stationInput = document.getElementById('temperatureStation');
                        if (stationInput) {
                            stationInput.value = stationId;
                        }
                    });
            } else {
                const stationInput = document.getElementById('temperatureStation');
                if (stationInput) {
                    stationInput.value = '';
                }
            }
            document.getElementById('temperatureUpdateInterval').value = temperature.update_interval_minutes || 60;
            document.getElementById('temperatureSensitivity').value = temperature.adjustment_sensitivity || 'medium';

            // Daylight settings
            document.getElementById('daylightEnabled').checked = daylight.enabled || false;
            document.getElementById('daylightShiftSchedule').checked = daylight.shift_schedule !== false;
            document.getElementById('daylightBoost').value = daylight.daylight_boost || 1.2;
            document.getElementById('nightReduction').value = daylight.night_reduction || 0.8;

            // Adaptation settings
            document.getElementById('adaptationEnabled').checked = adaptation.enabled || false;
        }
    } catch (error) {
        console.error('Error loading settings:', error);
        showMessage('Error loading settings: ' + error.message, 'error');
    }
}

async function saveSettings() {
    try {
        const schedule = await fetch(`${API_BASE}/config/schedule`).then(r => r.json());
        
        // Build adaptation config
        const adaptation = schedule.adaptation || {};
        
        // Location
        adaptation.location = {
            postcode: document.getElementById('postcode').value.trim(),
            timezone: document.getElementById('timezone').value
        };

        // Temperature - get station ID from the hidden field or current config
        // The station ID is stored when postcode lookup happens
        const stationInput = document.getElementById('temperatureStation');
        let stationId = 'auto';
        // Extract station ID from the display value if it's in format "Name (ID)"
        if (stationInput && stationInput.value) {
            const match = stationInput.value.match(/\((\d+)\)/);
            if (match) {
                stationId = match[1];
            }
        }
        
        adaptation.temperature = {
            enabled: document.getElementById('temperatureEnabled').checked,
            source: 'bom',
            station_id: stationId,
            update_interval_minutes: parseInt(document.getElementById('temperatureUpdateInterval').value) || 60,
            adjustment_sensitivity: document.getElementById('temperatureSensitivity').value
        };

        // Daylight
        adaptation.daylight = {
            enabled: document.getElementById('daylightEnabled').checked,
            shift_schedule: document.getElementById('daylightShiftSchedule').checked,
            daylight_boost: parseFloat(document.getElementById('daylightBoost').value) || 1.2,
            night_reduction: parseFloat(document.getElementById('nightReduction').value) || 0.8,
            update_frequency: 'daily'
        };

        // Master enable
        adaptation.enabled = document.getElementById('adaptationEnabled').checked;

        // Update schedule config
        schedule.adaptation = adaptation;

        const response = await fetch(`${API_BASE}/config/schedule`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(schedule)
        });

        const result = await response.json();
        if (response.ok) {
            showMessage('Settings saved successfully. Restart daemon for changes to take effect.', 'success');
        } else {
            showMessage(result.detail || result.message || 'Error saving settings', 'error');
        }
    } catch (error) {
        showMessage('Error saving settings: ' + error.message, 'error');
    }
}

function resetSettings() {
    if (confirm('Reset all settings to defaults? This will overwrite your current settings.')) {
        // Reset to defaults
        document.getElementById('postcode').value = '';
        document.getElementById('timezone').value = 'Australia/Sydney';
        document.getElementById('temperatureEnabled').checked = false;
        document.getElementById('temperatureStation').value = '';
        document.getElementById('temperatureUpdateInterval').value = 60;
        document.getElementById('temperatureSensitivity').value = 'medium';
        document.getElementById('daylightEnabled').checked = false;
        document.getElementById('daylightShiftSchedule').checked = true;
        document.getElementById('daylightBoost').value = 1.2;
        document.getElementById('nightReduction').value = 0.8;
        document.getElementById('adaptationEnabled').checked = false;
        
        showMessage('Settings reset to defaults. Click "Save Settings" to apply.', 'success');
    }
}

// Removed loadBOMStations - no longer needed since we use postcode lookup only

// Postcode lookup for nearest station
document.addEventListener('DOMContentLoaded', () => {
    const postcodeInput = document.getElementById('postcode');
    if (postcodeInput) {
        let postcodeLookupTimeout = null;
        
        postcodeInput.addEventListener('input', (e) => {
            clearTimeout(postcodeLookupTimeout);
            const postcode = e.target.value.trim();
            
            // Only lookup if postcode is 4 digits (Australian postcode format)
            if (postcode.length === 4 && /^\d{4}$/.test(postcode)) {
                postcodeLookupTimeout = setTimeout(async () => {
                    try {
                        const response = await fetch(`${API_BASE}/bom/nearest-station?postcode=${encodeURIComponent(postcode)}`);
                        if (response.ok) {
                            const data = await response.json();
                            
                            // Update the station input field with the station name
                            const stationInput = document.getElementById('temperatureStation');
                            if (stationInput) {
                                stationInput.value = `${data.station_name} (${data.station_id})`;
                                
                                // Show a message about the auto-selection
                                const stationSelectContainer = stationInput.closest('.form-group');
                                if (stationSelectContainer) {
                                    // Remove any existing message
                                    const existingMsg = stationSelectContainer.querySelector('.nearest-station-msg');
                                    if (existingMsg) {
                                        existingMsg.remove();
                                    }
                                    
                                    // Add message about nearest station
                                    const msg = document.createElement('small');
                                    msg.className = 'nearest-station-msg';
                                    msg.style.color = '#28a745';
                                    msg.style.display = 'block';
                                    msg.style.marginTop = '5px';
                                    msg.textContent = `✓ Station set: ${data.station_name} (${data.distance_km} km away)`;
                                    stationSelectContainer.appendChild(msg);
                                }
                            }
                        } else if (response.status === 404) {
                            // Postcode not found - clear station and message
                            const stationInput = document.getElementById('temperatureStation');
                            if (stationInput) {
                                stationInput.value = '';
                            }
                            const stationSelectContainer = stationInput?.closest('.form-group');
                            if (stationSelectContainer) {
                                const existingMsg = stationSelectContainer.querySelector('.nearest-station-msg');
                                if (existingMsg) {
                                    existingMsg.remove();
                                }
                            }
                        }
                    } catch (error) {
                        console.error('Error looking up nearest station:', error);
                    }
                }, 500); // Debounce postcode lookup
            } else if (postcode.length === 0) {
                // Clear station and message if postcode is cleared
                const stationInput = document.getElementById('temperatureStation');
                if (stationInput) {
                    stationInput.value = '';
                }
                const stationSelectContainer = stationInput?.closest('.form-group');
                if (stationSelectContainer) {
                    const existingMsg = stationSelectContainer.querySelector('.nearest-station-msg');
                    if (existingMsg) {
                        existingMsg.remove();
                    }
                }
            }
        });
    }
});


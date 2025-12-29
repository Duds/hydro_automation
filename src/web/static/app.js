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
    try {
        // Control buttons
        const startBtn = document.getElementById('startBtn');
        const stopBtn = document.getElementById('stopBtn');
        const deviceOnBtn = document.getElementById('deviceOnBtn');
        const deviceOffBtn = document.getElementById('deviceOffBtn');
        const emergencyStopBtn = document.getElementById('emergencyStopBtn');
        
        if (startBtn) {
            startBtn.addEventListener('click', startScheduler);
        } else {
            console.warn('startBtn not found');
        }
        if (stopBtn) {
            stopBtn.addEventListener('click', stopScheduler);
        } else {
            console.warn('stopBtn not found');
        }
        if (deviceOnBtn) {
            deviceOnBtn.addEventListener('click', turnDeviceOn);
        } else {
            console.warn('deviceOnBtn not found');
        }
        if (deviceOffBtn) {
            deviceOffBtn.addEventListener('click', turnDeviceOff);
        } else {
            console.warn('deviceOffBtn not found');
        }
        if (emergencyStopBtn) {
            emergencyStopBtn.addEventListener('click', emergencyStop);
        } else {
            console.warn('emergencyStopBtn not found');
        }

    // Schedule configuration buttons
    const addCycleBtn = document.getElementById('addCycleBtn');
    const saveScheduleConfigBtn = document.getElementById('saveScheduleConfig');
    const refreshLogsBtn = document.getElementById('refreshLogs');
    
    if (addCycleBtn) addCycleBtn.addEventListener('click', addCycle);
    if (saveScheduleConfigBtn) saveScheduleConfigBtn.addEventListener('click', saveScheduleConfig);
    if (refreshLogsBtn) refreshLogsBtn.addEventListener('click', loadLogs);
    
    // Schedule view toggle
    const scheduleViewToggle = document.getElementById('scheduleViewToggle');
    if (scheduleViewToggle) {
        scheduleViewToggle.addEventListener('change', switchScheduleView);
    }
    
    // Validation report button
    const validateScheduleBtn = document.getElementById('validateScheduleBtn');
    if (validateScheduleBtn) {
        validateScheduleBtn.addEventListener('click', showValidationReport);
    }

    // Settings buttons
    const saveSettingsBtn = document.getElementById('saveSettings');
    const resetSettingsBtn = document.getElementById('resetSettings');
    
    if (saveSettingsBtn) saveSettingsBtn.addEventListener('click', saveSettings);
    if (resetSettingsBtn) resetSettingsBtn.addEventListener('click', resetSettings);

    // Service management buttons
    const daemonStartBtn = document.getElementById('daemonStartBtn');
    const daemonStopBtn = document.getElementById('daemonStopBtn');
    const daemonRestartBtn = document.getElementById('daemonRestartBtn');
    const webappStartBtn = document.getElementById('webappStartBtn');
    const webappStopBtn = document.getElementById('webappStopBtn');
    const webappRestartBtn = document.getElementById('webappRestartBtn');
    
    if (daemonStartBtn) daemonStartBtn.addEventListener('click', () => controlService('daemon', 'start'));
    if (daemonStopBtn) daemonStopBtn.addEventListener('click', () => controlService('daemon', 'stop'));
    if (daemonRestartBtn) daemonRestartBtn.addEventListener('click', () => controlService('daemon', 'restart'));
    if (webappStartBtn) webappStartBtn.addEventListener('click', () => controlService('webapp', 'start'));
    if (webappStopBtn) webappStopBtn.addEventListener('click', () => controlService('webapp', 'stop'));
    if (webappRestartBtn) webappRestartBtn.addEventListener('click', () => controlService('webapp', 'restart'));

    // Auto-scroll checkbox
    const autoScrollCheckbox = document.getElementById('autoScroll');
    if (autoScrollCheckbox) {
        autoScrollCheckbox.addEventListener('change', (e) => {
            if (e.target.checked) {
                scrollLogsToBottom();
            }
        });
    }
    } catch (error) {
        console.error('Error setting up event listeners:', error);
    }
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
    // Load settings after a short delay to ensure DOM is ready
    setTimeout(() => loadSettings(), 100);
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
    
    // Update scheduler state with animation
    const state = status.scheduler_state || 'idle';
    const stateElement = document.getElementById('schedulerState');
    stateElement.textContent = state.charAt(0).toUpperCase() + state.slice(1);
    
    // Remove all state classes
    stateElement.classList.remove('flood', 'drain', 'idle', 'waiting');
    // Add appropriate class for animation
    if (state === 'flood') {
        stateElement.classList.add('flood');
    } else if (state === 'drain') {
        stateElement.classList.add('drain');
    } else if (state === 'waiting') {
        stateElement.classList.add('waiting');
    } else {
        stateElement.classList.add('idle');
    }
    
    // Update next event
    document.getElementById('nextEvent').textContent = 
        status.next_event_time || 'N/A';
    
    // Update time until next cycle
    document.getElementById('timeUntilNextCycle').textContent = 
        status.time_until_next_cycle || 'N/A';
    
    // Update current time period
    const periodElement = document.getElementById('currentTimePeriod');
    if (status.current_time_period) {
        const periodNames = {
            'morning': 'Morning',
            'day': 'Day',
            'evening': 'Evening',
            'night': 'Night'
        };
        periodElement.textContent = periodNames[status.current_time_period] || status.current_time_period;
        // Add period class for styling
        periodElement.classList.remove('period-morning', 'period-day', 'period-evening', 'period-night');
        periodElement.classList.add(`period-${status.current_time_period}`);
    } else {
        periodElement.textContent = 'N/A';
        periodElement.classList.remove('period-morning', 'period-day', 'period-evening', 'period-night');
    }

    // Update device status
    document.getElementById('deviceConnected').textContent = 
        status.device_connected ? 'Connected' : 'Disconnected';
    
    const deviceState = status.device_state === null ? 'Unknown' : 
                       status.device_state ? 'ON' : 'OFF';
    const deviceStateElement = document.getElementById('deviceState');
    deviceStateElement.textContent = deviceState;
    
    // Add animation classes for device state
    deviceStateElement.classList.remove('on', 'off');
    if (deviceState === 'ON') {
        deviceStateElement.classList.add('on');
    } else if (deviceState === 'OFF') {
        deviceStateElement.classList.add('off');
    }
    
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
        console.log('Starting scheduler...');
        const response = await fetch(`${API_BASE}/control/start`, {
            method: 'POST'
        });
        const result = await response.json();
        console.log('Start scheduler response:', result);
        if (result.success) {
            showMessage('Scheduler started', 'success');
            updateStatus();
        } else {
            showMessage(result.message, 'error');
        }
    } catch (error) {
        console.error('Error starting scheduler:', error);
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
        console.log('Turning device on...');
        const response = await fetch(`${API_BASE}/device/on`, {
            method: 'POST'
        });
        const result = await response.json();
        console.log('Turn device on response:', result);
        if (result.success) {
            showMessage('Device turned ON', 'success');
            // Refresh status immediately and again after a delay to ensure state updates
            updateStatus();
            setTimeout(() => {
                updateStatus();
            }, 1500);
        } else {
            showMessage(result.message, 'error');
        }
    } catch (error) {
        console.error('Error turning device on:', error);
        showMessage('Error turning device on: ' + error.message, 'error');
    }
}

async function turnDeviceOff() {
    try {
        console.log('Turning device off...');
        const response = await fetch(`${API_BASE}/device/off`, {
            method: 'POST'
        });
        const result = await response.json();
        console.log('Turn device off response:', result);
        if (result.success) {
            showMessage('Device turned OFF', 'success');
            // Refresh status immediately and again after a delay to ensure state updates
            updateStatus();
            setTimeout(() => {
                updateStatus();
            }, 1500);
        } else {
            showMessage(result.message, 'error');
        }
    } catch (error) {
        console.error('Error turning device off:', error);
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
let baseCycles = [];
let adaptedCycles = [];
let showingAdapted = false;
let adaptationEnabled = false;

async function loadScheduleConfig() {
    try {
        const response = await fetch(`${API_BASE}/config/schedule`);
        const config = await response.json();
        
        document.getElementById('scheduleType').textContent = config.type || 'interval';
        
        // Check if adaptation is enabled
        const adaptation = config.adaptation || {};
        adaptationEnabled = adaptation.enabled || false;
        
        // Load base cycles
        if (config.cycles && Array.isArray(config.cycles)) {
            baseCycles = config.cycles;
        } else if (config.on_times && Array.isArray(config.on_times)) {
            // Convert legacy on_times to cycles format
            baseCycles = config.on_times.map(time => ({
                on_time: time,
                off_duration_minutes: 0  // Default, will wait until next scheduled time
            }));
        } else {
            baseCycles = [];
        }
        
        // Check if adaptive is enabled
        const adaptiveEnabled = config.adaptation?.adaptive?.enabled || false;
        
        // If adaptation is enabled, fetch adapted cycles
        if (adaptationEnabled) {
            try {
                const adaptedResponse = await fetch(`${API_BASE}/config/schedule/adapted`);
                if (adaptedResponse.ok) {
                    const adaptedData = await adaptedResponse.json();
                    if (adaptedData.adapted && adaptedData.cycles && adaptedData.cycles.length > 0) {
                        // Map API response to cycle format with factor information
                        adaptedCycles = adaptedData.cycles.map(cycle => ({
                            on_time: cycle.on_time,
                            off_duration_minutes: cycle.off_duration_minutes,
                            period: cycle.period || cycle._period,
                            temperature: cycle.temperature !== undefined ? cycle.temperature : cycle._temp,
                            humidity: cycle.humidity !== undefined ? cycle.humidity : cycle._humidity,
                            temp_factor: cycle.temp_factor !== undefined ? cycle.temp_factor : cycle._temp_factor,
                            humidity_factor: cycle.humidity_factor !== undefined ? cycle.humidity_factor : cycle._humidity_factor
                        }));
                        showingAdapted = true; // Show adapted by default when available
                        console.log(`Loaded ${adaptedCycles.length} adapted cycles`);
                    } else {
                        adaptedCycles = [];
                        showingAdapted = false;
                        console.warn('Adaptation enabled but no adapted cycles available. Adaptation may still be initializing.');
                    }
                } else {
                    adaptedCycles = [];
                    showingAdapted = false;
                    console.warn(`Failed to fetch adapted schedule: HTTP ${adaptedResponse.status}`);
                }
            } catch (error) {
                console.error('Error fetching adapted schedule:', error);
                adaptedCycles = [];
                showingAdapted = false;
            }
        } else {
            adaptedCycles = [];
            showingAdapted = false;
        }
        
        // Set current cycles based on view
        // When adaptation is enabled, prioritize showing adapted cycles
        if (adaptiveEnabled && adaptedCycles.length > 0) {
            cycles = adaptedCycles;
            showingAdapted = true;
        } else if (adaptationEnabled) {
            // Legacy adaptive mode: show adapted cycles if available, otherwise show base but indicate adaptation is active
            if (adaptedCycles.length > 0) {
                cycles = showingAdapted ? adaptedCycles : baseCycles;
            } else {
                // Adaptation enabled but cycles not available yet - show base cycles but mark as adapted mode
                cycles = baseCycles;
                showingAdapted = false; // Don't show as "adapted" since cycles aren't available
            }
        } else {
            // No adaptation: show base cycles
            cycles = baseCycles;
            showingAdapted = false;
        }
        
        // Update UI
        updateScheduleViewControls();
        renderCyclesTable();
        await updateScheduleEditingState(adaptationEnabled);
    } catch (error) {
        console.error('Error loading schedule config:', error);
    }
}

function updateScheduleViewControls() {
    const viewControls = document.getElementById('scheduleViewControls');
    const viewTitle = document.getElementById('scheduleViewTitle');
    const viewToggle = document.getElementById('scheduleViewToggle');
    const viewLabel = document.getElementById('scheduleViewLabel');
    const validateBtn = document.getElementById('validateScheduleBtn');
    
    // Check if adaptive is enabled (cycles have period info)
    const adaptiveEnabled = cycles.length > 0 && cycles[0].period !== undefined;
    
    if (adaptiveEnabled) {
        // Adaptive mode - show validation button, hide toggle
        if (viewControls) {
            viewControls.style.display = 'none';
        }
        if (validateBtn) {
            validateBtn.style.display = 'inline-block';
        }
        if (viewTitle) {
            viewTitle.textContent = 'Adaptive Schedule (Generated)';
            viewTitle.className = 'schedule-view-title';
        }
    } else if (adaptationEnabled) {
        // Legacy adaptive mode - show toggle controls if adapted cycles are available
        if (adaptedCycles.length > 0) {
            // Have adapted cycles - show toggle controls
            if (viewControls) {
                viewControls.style.display = 'flex';
            }
            if (validateBtn) {
                validateBtn.style.display = 'none';
            }
            
            // Update toggle state
            if (viewToggle) {
                viewToggle.checked = showingAdapted;
            }
            
            // Update label and title
            if (viewLabel) {
                viewLabel.textContent = showingAdapted ? 'View: Adapted' : 'View: Base';
            }
            
            if (viewTitle) {
                viewTitle.textContent = showingAdapted ? 'Schedule Cycles (Adapted - Calculated)' : 'Schedule Cycles (Base)';
                viewTitle.className = showingAdapted ? 'schedule-view-title' : '';
            }
        } else {
            // Adaptation enabled but cycles not available yet - show base with adaptation indicator
            if (viewControls) {
                viewControls.style.display = 'none';
            }
            if (validateBtn) {
                validateBtn.style.display = 'none';
            }
            
            if (viewTitle) {
                viewTitle.textContent = 'Schedule Cycles (Adaptation Active - Cycles Loading...)';
                viewTitle.className = 'schedule-view-title';
            }
        }
    } else {
        // No adaptation - hide everything
        if (viewControls) {
            viewControls.style.display = 'none';
        }
        if (validateBtn) {
            validateBtn.style.display = 'none';
        }
        
        if (viewTitle) {
            viewTitle.textContent = 'Schedule Cycles';
            viewTitle.className = '';
        }
    }
}

function switchScheduleView() {
    if (!adaptationEnabled || adaptedCycles.length === 0) {
        return;
    }
    
    showingAdapted = !showingAdapted;
    cycles = showingAdapted ? adaptedCycles : baseCycles;
    
    updateScheduleViewControls();
    renderCyclesTable();
}

function renderCyclesTable() {
    const tbody = document.getElementById('cyclesTableBody');
    const thead = document.getElementById('cyclesTableHead');
    tbody.innerHTML = '';
    
    if (cycles.length === 0) {
        const row = document.createElement('tr');
        const isAdaptive = false; // No cycles, so can't be adaptive
        const colspan = isAdaptive ? 6 : 3;
        row.innerHTML = `<td colspan="${colspan}" style="text-align: center; padding: 20px; color: #666;">No cycles defined</td>`;
        tbody.appendChild(row);
        return;
    }
    
    // Sort cycles by time
    cycles.sort((a, b) => {
        const timeA = parseTimeForSort(a.on_time);
        const timeB = parseTimeForSort(b.on_time);
        return timeA - timeB;
    });
    
    // Check if adaptive is enabled and we're showing adaptive cycles
    const isAdaptive = cycles.length > 0 && cycles[0].period !== undefined;
    // Schedule is read-only when adaptation is enabled (regardless of whether showing adapted or base cycles)
    const isReadOnly = adaptationEnabled || isAdaptive;
    
    // Update table header for adaptive
    if (isAdaptive && thead) {
        thead.innerHTML = `
            <tr>
                <th>ON Time</th>
                <th>OFF Duration (min)</th>
                <th>Period</th>
                <th>Temp (°C)</th>
                <th>Humidity (%)</th>
                <th>Factors</th>
            </tr>
        `;
    } else if (thead) {
        thead.innerHTML = `
            <tr>
                <th>ON Time</th>
                <th>OFF Duration (min)</th>
                <th>Actions</th>
            </tr>
        `;
    }
    
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
        
        // Format OFF duration for display
        const offDuration = cycle.off_duration_minutes || 0;
        const offDurationDisplay = offDuration.toFixed(1);
        
        if (isAdaptive) {
            // Adaptive display with factor breakdown
            const period = cycle.period || cycle._period || '-';
            const temp = cycle.temperature !== undefined ? cycle.temperature : (cycle._temp !== undefined ? cycle._temp : null);
            const humidity = cycle.humidity !== undefined ? cycle.humidity : (cycle._humidity !== undefined ? cycle._humidity : null);
            const tempFactor = cycle.temp_factor !== undefined ? cycle.temp_factor : (cycle._temp_factor !== undefined ? cycle._temp_factor : null);
            const humidityFactor = cycle.humidity_factor !== undefined ? cycle.humidity_factor : (cycle._humidity_factor !== undefined ? cycle._humidity_factor : null);
            
            const tempDisplay = temp !== null && temp !== undefined ? `${temp.toFixed(1)}°C` : 'N/A';
            const humidityDisplay = humidity !== null && humidity !== undefined ? `${humidity.toFixed(0)}%` : 'N/A';
            const factorsDisplay = tempFactor !== null && humidityFactor !== null 
                ? `T:${tempFactor.toFixed(2)} H:${humidityFactor.toFixed(2)}`
                : '-';
            
            row.innerHTML = `
                <td>
                    <span style="font-weight: 500; color: #667eea;">${timeValue || '00:00'}</span>
                </td>
                <td>
                    <span style="font-weight: 500; color: #667eea;">${offDurationDisplay}</span>
                </td>
                <td>
                    <span style="color: #666; font-size: 0.9em; text-transform: capitalize;">${period}</span>
                </td>
                <td>
                    <span style="color: #666; font-size: 0.9em;">${tempDisplay}</span>
                </td>
                <td>
                    <span style="color: #666; font-size: 0.9em;">${humidityDisplay}</span>
                </td>
                <td>
                    <span style="color: #666; font-size: 0.85em;" title="Temperature factor: ${tempFactor !== null ? tempFactor.toFixed(3) : 'N/A'}, Humidity factor: ${humidityFactor !== null ? humidityFactor.toFixed(3) : 'N/A'}">${factorsDisplay}</span>
                </td>
            `;
        } else if (isReadOnly) {
            // Read-only display - show "Calculated" if showing adapted cycles, otherwise show adaptation status
            const readOnlyLabel = showingAdapted ? 'Calculated' : (adaptationEnabled ? 'Adapted' : 'Read-only');
            row.innerHTML = `
                <td>
                    <span style="font-weight: 500; color: #667eea;">${timeValue || '00:00'}</span>
                </td>
                <td>
                    <span style="font-weight: 500; color: #667eea;">${offDurationDisplay}</span>
                </td>
                <td>
                    <span style="color: #666; font-size: 0.9em;" title="${adaptationEnabled ? 'Schedule is automatically adjusted based on environmental factors' : 'Schedule is read-only'}">${readOnlyLabel}</span>
                </td>
            `;
        } else {
            // Editable display for base cycles
            row.innerHTML = `
                <td>
                    <input type="time" class="cycle-on-time" value="${timeValue || '00:00'}" data-index="${index}">
                </td>
                <td>
                    <input type="number" class="cycle-off-duration" value="${offDurationDisplay}" 
                           step="0.1" min="0" data-index="${index}">
                </td>
                <td>
                    <button class="btn btn-danger btn-small remove-cycle" data-index="${index}">Remove</button>
                </td>
            `;
        }
        
        tbody.appendChild(row);
    });
    
    // Add event listeners only for editable inputs
    if (!isReadOnly) {
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
                // Re-check adaptation status after removing cycle
                updateEnvironment();
            });
        });
    }
}

function parseTimeForSort(timeStr) {
    const parts = timeStr.split(':');
    return parseInt(parts[0]) * 60 + parseInt(parts[1]);
}

async function showValidationReport() {
    try {
        const response = await fetch(`${API_BASE}/config/schedule/adaptive/validate`);
        if (response.ok) {
            const data = await response.json();
            const report = data.report || 'No validation report available.';
            const comparison = data.comparison || {};
            
            // Show report in a modal or alert
            const reportText = `Validation Report\n\n${report}\n\nWarnings: ${data.warnings_count || 0}\nDeviations: ${data.deviations_count || 0}\nMatches: ${data.matches_count || 0}`;
            alert(reportText);
        } else {
            const error = await response.json();
            showMessage(error.detail || 'Error generating validation report', 'error');
        }
    } catch (error) {
        showMessage('Error generating validation report: ' + error.message, 'error');
    }
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
    // Refresh environment and schedule config to get latest state
    // This ensures we have the most up-to-date adaptation status
    try {
        const [envResponse, scheduleResponse] = await Promise.all([
            fetch(`${API_BASE}/environment`),
            fetch(`${API_BASE}/config/schedule`)
        ]);
        
        if (envResponse.ok) {
            const env = await envResponse.json();
            if (env.adaptation_enabled) {
                showMessage('Schedule editing is disabled when adaptation is enabled. Disable adaptation in Settings first.', 'error');
                return;
            }
        }
        
        if (scheduleResponse.ok) {
            const schedule = await scheduleResponse.json();
            const adaptive = schedule.adaptation?.adaptive?.enabled || false;
            
            if (adaptive) {
                showMessage('Schedule editing is disabled when Adaptive Scheduling is enabled. Disable it in Settings first.', 'error');
                return;
            }
        }
    } catch (error) {
        console.error('Error checking adaptation status:', error);
        // Continue anyway - backend will validate
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
                    cycles: cycles
                })
        });
        
        if (response.status === 403) {
            const result = await response.json();
            showMessage(result.detail || 'Schedule editing is disabled when adaptation is enabled', 'error');
            return;
        }
        
        const result = await response.json();
        if (result.success) {
            showMessage(result.message, 'success');
            // Reload schedule config to reflect any changes
            await loadScheduleConfig();
            // Refresh environment data
            updateEnvironment();
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
            
            // Update humidity
            if (env.humidity !== null && env.humidity !== undefined) {
                document.getElementById('humidity').textContent = `${env.humidity}%`;
            } else {
                document.getElementById('humidity').textContent = 'N/A';
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
            
            // Update adaptive status
            document.getElementById('adaptiveStatus').textContent =
                env.adaptive_enabled ? 'Enabled' : 'Disabled';
            
            // Update schedule editing state based on adaptation
            await updateScheduleEditingState(env.adaptation_enabled);
        }
    } catch (error) {
        console.error('Error fetching environment data:', error);
    }
}

async function updateScheduleEditingState(adaptationEnabled) {
    // Check if adaptive is enabled
    let adaptiveEnabled = false;
    try {
        const schedule = await fetch(`${API_BASE}/config/schedule`).then(r => r.json()).catch(() => ({}));
        adaptiveEnabled = schedule.adaptation?.adaptive?.enabled || false;
    } catch (e) {
        // Ignore errors
    }
    
    // Get schedule editing elements
    const addCycleBtn = document.getElementById('addCycleBtn');
    const saveScheduleBtn = document.getElementById('saveScheduleConfig');
    const cyclesTableBody = document.getElementById('cyclesTableBody');
    const adaptiveInfo = document.getElementById('adaptiveInfo');
    
    // Hide adaptive info (user doesn't want it displayed)
    if (adaptiveInfo) {
        adaptiveInfo.style.display = 'none';
    }
    
    // Disable/enable inputs
    if (addCycleBtn) {
        addCycleBtn.disabled = adaptationEnabled || adaptiveEnabled;
    }
    if (saveScheduleBtn) {
        saveScheduleBtn.disabled = adaptationEnabled || adaptiveEnabled;
    }
    
    // Disable cycle editing inputs
    if (cyclesTableBody) {
        const cycleInputs = cyclesTableBody.querySelectorAll('input, button');
        cycleInputs.forEach(input => {
            input.disabled = adaptationEnabled || adaptiveEnabled;
        });
    }
    
    // Show/hide info message
    let infoBox = document.querySelector('#scheduleTab .info-box');
    if (!infoBox) {
        // Create info box if it doesn't exist
        const scheduleTab = document.getElementById('scheduleTab');
        const configPanel = scheduleTab.querySelector('.config-panel');
        infoBox = document.createElement('div');
        infoBox.className = 'info-box';
        configPanel.insertBefore(infoBox, configPanel.firstChild);
    }
    
    if (adaptiveEnabled) {
        // Remove any existing adaptive message (user doesn't want it displayed)
        const warningMsg = infoBox.querySelector('.adaptation-warning');
        if (warningMsg) {
            warningMsg.remove();
        }
    } else if (adaptationEnabled) {
        // Update or add adaptation warning
        let warningMsg = infoBox.querySelector('.adaptation-warning');
        if (!warningMsg) {
            warningMsg = document.createElement('p');
            warningMsg.className = 'adaptation-warning';
            warningMsg.style.color = '#d32f2f';
            warningMsg.style.fontWeight = 'bold';
            infoBox.appendChild(warningMsg);
        }
        warningMsg.textContent = '⚠️ Schedule editing is disabled because adaptation is enabled. ' +
                                'The schedule is automatically adjusted based on temperature and daylight. ' +
                                'Disable adaptation in Settings to edit the schedule manually.';
    } else {
        // Remove warning if adaptation is disabled
        const warningMsg = infoBox.querySelector('.adaptation-warning');
        if (warningMsg) {
            warningMsg.remove();
        }
    }
}

// Helper function to safely set element value
function setElementValue(id, value) {
    const el = document.getElementById(id);
    if (el) {
        el.value = value;
    }
}

// Helper function to safely set checkbox checked state
function setElementChecked(id, checked) {
    const el = document.getElementById(id);
    if (el) {
        el.checked = checked;
    }
}

async function loadSettings() {
    try {
        // Wait a bit to ensure DOM is ready
        if (document.readyState === 'loading') {
            await new Promise(resolve => {
                if (document.readyState === 'loading') {
                    document.addEventListener('DOMContentLoaded', resolve);
                } else {
                    resolve();
                }
            });
        }
        
        const response = await fetch(`${API_BASE}/config/schedule`);
        if (response.ok) {
            const schedule = await response.json();
            const adaptation = schedule.adaptation || {};
            const location = adaptation.location || {};
            const temperature = adaptation.temperature || {};
            const daylight = adaptation.daylight || {};
            
            // Update schedule editing state based on adaptation
            updateScheduleEditingState(adaptation.enabled || false);

            // Location settings
            setElementValue('postcode', location.postcode || '');
            setElementValue('timezone', location.timezone || 'Australia/Sydney');

            // Temperature settings
            setElementChecked('temperatureEnabled', temperature.enabled || false);
            const stationId = temperature.station_id;
            // Display station name if we have a station ID
            if (stationId && stationId !== 'auto') {
                // Fetch station name to display
                fetch(`${API_BASE}/bom/stations/${stationId}`)
                    .then(r => r.json())
                    .then(station => {
                        setElementValue('temperatureStation', `${station.name} (${station.id})`);
                    })
                    .catch(() => {
                        // If fetch fails, just show the ID
                        setElementValue('temperatureStation', stationId);
                    });
            } else {
                setElementValue('temperatureStation', '');
            }
            setElementValue('temperatureUpdateInterval', temperature.update_interval_minutes || 60);
            setElementValue('temperatureSensitivity', temperature.adjustment_sensitivity || 'medium');

            // Daylight settings
            setElementChecked('daylightEnabled', daylight.enabled || false);
            setElementChecked('daylightShiftSchedule', daylight.shift_schedule !== false);
            
            // Period-based factors
            const periodFactors = daylight.period_factors || {};
            setElementValue('morningFactor', periodFactors.morning !== undefined ? periodFactors.morning : 1.556);
            setElementValue('dayFactor', periodFactors.day !== undefined ? periodFactors.day : 1.0);
            setElementValue('eveningFactor', periodFactors.evening !== undefined ? periodFactors.evening : 1.556);
            setElementValue('nightFactor', periodFactors.night !== undefined ? periodFactors.night : 0.237);
            
            // Legacy settings (for backward compatibility)
            setElementValue('daylightBoost', daylight.daylight_boost || 1.2);
            setElementValue('nightReduction', daylight.night_reduction || 0.8);

            // Adaptation settings
            setElementChecked('adaptationEnabled', adaptation.enabled || false);
            
            // System settings - flood duration
            if (schedule.flood_duration_minutes !== undefined) {
                setElementValue('floodDuration', schedule.flood_duration_minutes);
            }
            
            // Adaptive settings
            const adaptive = adaptation.adaptive || {};
            const adaptiveEnabled = adaptive.enabled || false;
            setElementChecked('adaptiveEnabled', adaptiveEnabled);
            
            // Show/hide adaptive settings
            const adaptiveSettings = document.getElementById('adaptiveSettings');
            if (adaptiveSettings) {
                adaptiveSettings.style.display = adaptiveEnabled ? 'block' : 'none';
            }
            
            // Load adaptive config
            if (adaptiveEnabled) {
                const todFreq = adaptive.tod_frequencies || {};
                setElementValue('todMorning', todFreq.morning || 18.0);
                setElementValue('todDay', todFreq.day || 28.0);
                setElementValue('todEvening', todFreq.evening || 18.0);
                setElementValue('todNight', todFreq.night || 118.0);
                
                const tempBands = adaptive.temperature_bands || {};
                if (tempBands.cold) {
                    setElementValue('tempColdMax', tempBands.cold.max || 15);
                    setElementValue('tempColdFactor', tempBands.cold.factor || 1.15);
                }
                if (tempBands.normal) {
                    setElementValue('tempNormalMin', tempBands.normal.min || 15);
                    setElementValue('tempNormalMax', tempBands.normal.max || 25);
                    setElementValue('tempNormalFactor', tempBands.normal.factor || 1.0);
                }
                if (tempBands.warm) {
                    setElementValue('tempWarmMin', tempBands.warm.min || 25);
                    setElementValue('tempWarmMax', tempBands.warm.max || 30);
                    setElementValue('tempWarmFactor', tempBands.warm.factor || 0.85);
                }
                if (tempBands.hot) {
                    setElementValue('tempHotMin', tempBands.hot.min || 30);
                    setElementValue('tempHotFactor', tempBands.hot.factor || 0.70);
                }
                
                const humidityBands = adaptive.humidity_bands || {};
                if (humidityBands.low) {
                    setElementValue('humidityLowMax', humidityBands.low.max || 40);
                    setElementValue('humidityLowFactor', humidityBands.low.factor || 0.9);
                }
                if (humidityBands.normal) {
                    setElementValue('humidityNormalMin', humidityBands.normal.min || 40);
                    setElementValue('humidityNormalMax', humidityBands.normal.max || 70);
                    setElementValue('humidityNormalFactor', humidityBands.normal.factor || 1.0);
                }
                if (humidityBands.high) {
                    setElementValue('humidityHighMin', humidityBands.high.min || 70);
                    setElementValue('humidityHighFactor', humidityBands.high.factor || 1.1);
                }
                
                const constraints = adaptive.constraints || {};
                setElementValue('minWaitDuration', constraints.min_wait_duration || 5);
                setElementValue('maxWaitDuration', constraints.max_wait_duration || 180);
                setElementValue('minFloodDuration', constraints.min_flood_duration || 2);
                setElementValue('maxFloodDuration', constraints.max_flood_duration || 15);
            }
        }
    } catch (error) {
        console.error('Error loading settings:', error);
        showMessage('Error loading settings: ' + error.message, 'error');
    }
}

// Toggle adaptive settings visibility
document.addEventListener('DOMContentLoaded', () => {
    const adaptiveCheckbox = document.getElementById('adaptiveEnabled');
    const adaptiveSettings = document.getElementById('adaptiveSettings');
    
    if (adaptiveCheckbox && adaptiveSettings) {
        adaptiveCheckbox.addEventListener('change', (e) => {
            adaptiveSettings.style.display = e.target.checked ? 'block' : 'none';
        });
    }
});

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
            // Period-based factors (new)
            period_factors: {
                morning: parseFloat(document.getElementById('morningFactor').value) || 1.556,
                day: parseFloat(document.getElementById('dayFactor').value) || 1.0,
                evening: parseFloat(document.getElementById('eveningFactor').value) || 1.556,
                night: parseFloat(document.getElementById('nightFactor').value) || 0.237
            },
            // Legacy settings (for backward compatibility)
            daylight_boost: parseFloat(document.getElementById('daylightBoost').value) || 1.2,
            night_reduction: parseFloat(document.getElementById('nightReduction').value) || 0.8,
            update_frequency: 'daily'
        };

        // Master enable
        adaptation.enabled = document.getElementById('adaptationEnabled').checked;
        
        // System settings - flood duration
        schedule.flood_duration_minutes = parseFloat(document.getElementById('floodDuration').value) || 2.0;
        
        // Adaptive settings
        const adaptiveEnabled = document.getElementById('adaptiveEnabled').checked;
        adaptation.adaptive = {
            enabled: adaptiveEnabled,
            tod_frequencies: {
                morning: parseFloat(document.getElementById('todMorning').value) || 18.0,
                day: parseFloat(document.getElementById('todDay').value) || 28.0,
                evening: parseFloat(document.getElementById('todEvening').value) || 18.0,
                night: parseFloat(document.getElementById('todNight').value) || 120.0
            },
            temperature_bands: {
                cold: {
                    max: parseFloat(document.getElementById('tempColdMax').value) || 15,
                    factor: parseFloat(document.getElementById('tempColdFactor').value) || 1.15
                },
                normal: {
                    min: parseFloat(document.getElementById('tempNormalMin').value) || 15,
                    max: parseFloat(document.getElementById('tempNormalMax').value) || 25,
                    factor: parseFloat(document.getElementById('tempNormalFactor').value) || 1.0
                },
                warm: {
                    min: parseFloat(document.getElementById('tempWarmMin').value) || 25,
                    max: parseFloat(document.getElementById('tempWarmMax').value) || 30,
                    factor: parseFloat(document.getElementById('tempWarmFactor').value) || 0.85
                },
                hot: {
                    min: parseFloat(document.getElementById('tempHotMin').value) || 30,
                    factor: parseFloat(document.getElementById('tempHotFactor').value) || 0.70
                }
            },
            humidity_bands: {
                low: {
                    max: parseFloat(document.getElementById('humidityLowMax').value) || 40,
                    factor: parseFloat(document.getElementById('humidityLowFactor').value) || 0.9
                },
                normal: {
                    min: parseFloat(document.getElementById('humidityNormalMin').value) || 40,
                    max: parseFloat(document.getElementById('humidityNormalMax').value) || 70,
                    factor: parseFloat(document.getElementById('humidityNormalFactor').value) || 1.0
                },
                high: {
                    min: parseFloat(document.getElementById('humidityHighMin').value) || 70,
                    factor: parseFloat(document.getElementById('humidityHighFactor').value) || 1.1
                }
            },
            constraints: {
                min_wait_duration: parseInt(document.getElementById('minWaitDuration').value) || 5,
                max_wait_duration: parseInt(document.getElementById('maxWaitDuration').value) || 180,
                min_flood_duration: parseFloat(document.getElementById('minFloodDuration').value) || 2,
                max_flood_duration: parseFloat(document.getElementById('maxFloodDuration').value) || 15
            }
        };

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
            // Reload schedule config to get updated state
            await loadScheduleConfig();
            // Update schedule editing state after saving adaptation settings
            updateScheduleEditingState(adaptation.enabled);
            // Refresh environment data to get updated adaptation status
            updateEnvironment();
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
        setElementValue('postcode', '');
        setElementValue('timezone', 'Australia/Sydney');
        setElementChecked('temperatureEnabled', false);
        setElementValue('temperatureStation', '');
        setElementValue('temperatureUpdateInterval', 60);
        setElementValue('temperatureSensitivity', 'medium');
        setElementChecked('daylightEnabled', false);
        setElementChecked('daylightShiftSchedule', true);
        setElementValue('morningFactor', 1.556);
        setElementValue('dayFactor', 1.0);
        setElementValue('eveningFactor', 1.556);
        setElementValue('nightFactor', 0.237);
        setElementValue('daylightBoost', 1.2);
        setElementValue('nightReduction', 0.8);
        setElementChecked('adaptationEnabled', false);
        
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


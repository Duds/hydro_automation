# Tapo P100 Hydroponic Flood & Drain Controller

A Python application to control a TP-Link Tapo P100 smart plug via WiFi for automating flood and drain cycles in a hydroponic system. This solution overcomes the Tapo app's 32-event limit by running unlimited cycles locally on your Mac.

## Features

- **Unlimited Cycles**: No restriction on the number of flood/drain cycles (unlike Tapo app's 32-event limit)
- **Flexible Scheduling**: Configurable flood duration, drain duration, and cycle intervals
- **Time-based Scheduling**: Optional active hours (e.g., only cycle during daylight hours)
- **Web UI**: Simple web interface for monitoring and control (accessible on local network)
- **Error Recovery**: Automatic retry on connection failures with device state verification
- **Graceful Shutdown**: Safe shutdown ensures the pump turns off on interruption
- **Logging**: Comprehensive logging of all cycle events for troubleshooting
- **Mac Sleep Prevention**: Integration with system tools to keep Mac awake

## Requirements

- Python 3.7 or higher
- macOS (for sleep prevention features)
- TP-Link Tapo P100 smart plug
- Tapo account (email and password)
- Tapo P100 connected to the same WiFi network as your Mac
- **Note**: This project uses the `plugp100` library which supports newer Tapo firmware (including KLAP V2 protocol). If you have older firmware, it will auto-detect and use the appropriate protocol.

## Installation

1. **Clone or download this repository**

2. **Create and activate a virtual environment** (recommended):
   ```bash
   # Create virtual environment
   python3 -m venv venv
   
   # Activate virtual environment
   source venv/bin/activate
   ```

   **Note**: Using a virtual environment is recommended to isolate dependencies. If you prefer to use your global Python installation, you can skip this step, but be aware it may cause conflicts with other projects.

3. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure the application**:
   ```bash
   cp config/config.json.example config/config.json
   ```

5. **Edit `config/config.json`** with your device details:
   - Tapo P100 IP address
   - Tapo account email
   - Tapo account password
   - Cycle timings (flood duration, drain duration, interval)
   - Schedule settings (optional)

## Finding Your Tapo P100 IP Address

If you don't know your Tapo P100 IP address, you can use the discovery script:

```bash
python -m src.discover_device --scan --email your_email@example.com --password your_password
```

Or test a specific IP address:

```bash
python -m src.discover_device --ip 192.168.1.XXX --email your_email@example.com --password your_password
```

Alternatively, you can:
- Check your router's device list
- Use the Tapo app to find the device IP address
- Check your router's DHCP client list

## Configuration

The configuration file (`config/config.json`) uses the following structure:

```json
{
  "device": {
    "ip_address": "192.168.1.XXX",
    "email": "your_tapo_email@example.com",
    "password": "your_tapo_password"
  },
  "cycle": {
    "flood_duration_minutes": 15,
    "drain_duration_minutes": 30,
    "interval_minutes": 120
  },
  "schedule": {
    "enabled": true,
    "active_hours": {
      "start": "06:00",
      "end": "22:00"
    }
  },
  "logging": {
    "log_file": "logs/hydro_controller.log",
    "log_level": "INFO"
  }
}
```

### Configuration Options

- **device.ip_address**: IP address of your Tapo P100 on your local network (used as initial/default)
- **device.email**: Your Tapo account email address
- **device.password**: Your Tapo account password
- **device.auto_discovery**: If `true`, automatically discover device on network if configured IP fails (default: `true`)
- **cycle.flood_duration_minutes**: How long to keep the pump ON (flood phase)
- **cycle.drain_duration_minutes**: How long to keep the pump OFF (drain phase)
- **cycle.interval_minutes**: Time between cycle starts (includes flood + drain + wait time)
- **schedule.enabled**: Enable/disable time-based scheduling
- **schedule.active_hours.start**: Start time for active cycle hours (HH:MM format)
- **schedule.active_hours.end**: End time for active cycle hours (HH:MM format)
- **logging.log_file**: Path to log file (will be created automatically)
- **logging.log_level**: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- **web.enabled**: Enable/disable web UI (default: `false`)
- **web.host**: Host to bind web server to (default: `"0.0.0.0"` for all interfaces)
- **web.port**: Port for web server (default: `8000`)

## Usage

### Basic Usage

Run the controller:

```bash
python -m src.main
```

Or with a custom config file:

```bash
python -m src.main --config path/to/config.json
```

### Web UI

The controller includes a simple web interface for monitoring and control. To enable it:

**Option 1: Using command line flag**
```bash
python -m src.main --web
```

**Option 2: Enable in configuration file**

Edit `config/config.json` and add:
```json
{
  "web": {
    "enabled": true,
    "host": "0.0.0.0",
    "port": 8000
  }
}
```

Then run normally:
```bash
python -m src.main
```

**Accessing the Web UI:**

Once started, the web UI will be available at:
- `http://localhost:8000` (from the Mac)
- `http://<mac-ip-address>:8000` (from any device on your local network)

**Web UI Features:**
- Real-time system status and device state
- Start/Stop scheduler controls
- Manual device control (ON/OFF)
- Emergency stop
- View and edit cycle configuration
- Real-time log viewer
- Responsive design for mobile and desktop

**Note:** The web UI is accessible only on your local network. For remote access, use a VPN or SSH tunnel.

### Preventing Mac from Sleeping

To ensure your Mac stays awake while running the controller, you have several options:

#### Option 1: Using the provided script (in a separate terminal)

```bash
./scripts/prevent_sleep.sh
```

#### Option 2: Using caffeinate directly

```bash
caffeinate -d -i -m -u
```

#### Option 3: System Settings (Recommended for long-term use)

1. Go to **System Settings** > **Battery** (or **Energy Saver** on older macOS)
2. Adjust settings to prevent sleep:
   - Disable "Put hard disks to sleep when possible"
   - Adjust "Turn display off after" to a longer time or "Never"
   - Enable "Prevent automatic sleeping when the display is off"

#### Option 4: Using Amphetamine (Mac App Store)

- Download [Amphetamine](https://apps.apple.com/au/app/amphetamine/id937984704) from the Mac App Store
- Configure it to keep your Mac awake indefinitely or on a schedule

### Running as a Background Daemon

To run the controller as a background daemon on macOS (so it continues running after closing your IDE), you have several options:

#### Option 1: Using launchd (Recommended - Most Robust)

The easiest way is to use the provided installation script:

```bash
./scripts/install_daemon.sh
```

This will:
- Create a launchd plist file
- Install it as a user daemon
- Start the service automatically
- Configure it to restart if it crashes
- Set up logging

**Useful commands:**
```bash
# Check if service is running
launchctl list | grep com.hydro.controller

# View logs
tail -f logs/daemon.stdout.log
tail -f logs/daemon.stderr.log

# Stop the service
launchctl stop com.hydro.controller

# Start the service
launchctl start com.hydro.controller

# Uninstall the daemon
./scripts/uninstall_daemon.sh
```

**Manual Installation** (if you prefer to do it manually):

1. Create a plist file at `~/Library/LaunchAgents/com.hydro.controller.plist` with your project paths
2. Load it: `launchctl load ~/Library/LaunchAgents/com.hydro.controller.plist`
3. Start it: `launchctl start com.hydro.controller`

#### Option 2: Using nohup (Simple Background Process)

For a simpler approach that doesn't require launchd:

```bash
./scripts/run_background.sh
```

Or manually:
```bash
nohup python -m src.main > logs/background.log 2>&1 &
```

**Note**: This method won't automatically restart if the process crashes, but it's simpler for testing.

#### Option 3: Using screen or tmux (For Development)

If you want to keep the terminal session accessible:

```bash
# Using screen
screen -S hydro
python -m src.main
# Press Ctrl+A then D to detach

# Reattach later with:
screen -r hydro

# Using tmux
tmux new -s hydro
python -m src.main
# Press Ctrl+B then D to detach

# Reattach later with:
tmux attach -t hydro
```

**Recommendation**: Use Option 1 (launchd) for production use as it provides automatic restart on crashes and proper logging.

## Cycle Operation

The controller follows this cycle pattern:

1. **Flood Phase**: Device turns ON for `flood_duration_minutes`
2. **Drain Phase**: Device turns OFF for `drain_duration_minutes`
3. **Wait Phase**: Waits for `interval_minutes` before starting the next cycle

The cycle repeats continuously (or during active hours if scheduling is enabled).

Example with default settings:
- Flood: 15 minutes (pump ON)
- Drain: 30 minutes (pump OFF)
- Interval: 120 minutes (2 hours between cycle starts)
- Total cycle time: ~45 minutes (15 + 30)
- Wait time: ~75 minutes (120 - 45)

## Logging

Logs are written to `logs/hydro_controller.log` by default (configurable in config.json). Logs include:

- Connection events
- Cycle start/stop events
- Device state changes
- Errors and warnings
- Scheduler status

Log files are automatically rotated when they reach 10MB, keeping the last 5 backup files.

## Troubleshooting

### Device Connection Issues

1. **Verify IP address**: Use the discovery script to test connection
2. **Check network**: Ensure device and Mac are on the same WiFi network
3. **Check credentials**: Verify email and password are correct
4. **Restart device**: Try unplugging and replugging the Tapo P100

### IP Address Changes

If your Tapo P100 gets a new IP address from your router (DHCP reallocation):

- **Automatic Discovery**: The controller has automatic device discovery enabled by default. If the configured IP address fails, it will automatically scan the network to find your device.

- **Update Configuration**: After the device is found via discovery, you'll see a log message with the new IP address. Consider updating `config.json` with the new IP for faster initial connection.

- **Static IP Recommendation**: For best reliability, configure your router to assign a static/reserved IP address to your Tapo P100 based on its MAC address. This prevents IP address changes.

- **Disable Auto-Discovery**: If you prefer to always use the configured IP address, set `"auto_discovery": false` in your device configuration.

### Device Not Responding

- The controller includes automatic retry logic
- Check logs for specific error messages
- Verify the device is online using the Tapo app

### Mac Goes to Sleep

- Ensure sleep prevention is active (caffeinate or system settings)
- Check Energy Saver settings
- Consider using Amphetamine for more reliable sleep prevention

### Configuration Errors

- Verify JSON syntax is correct
- Check all required fields are present
- Ensure time values are in correct format (HH:MM)

## Safety Features

- **Graceful Shutdown**: On shutdown (Ctrl+C or SIGTERM), the controller ensures the device is turned OFF before exiting
- **State Verification**: Device state is verified after each on/off command
- **Error Recovery**: Automatic retry on connection failures
- **Network Resilience**: Handles network interruptions gracefully
- **Auto-Discovery**: Automatically finds device on network if IP address changes (DHCP reallocation)

## Development

### Project Structure

```
hydro_automation/
├── config/
│   └── config.json.example    # Configuration template
├── src/
│   ├── __init__.py
│   ├── main.py                # Main application entry point
│   ├── tapo_controller.py     # Tapo P100 device controller
│   ├── scheduler.py           # Cycle scheduler
│   ├── logger.py              # Logging configuration
│   └── discover_device.py     # Device discovery script
├── scripts/
│   └── prevent_sleep.sh       # Mac sleep prevention script
├── logs/                      # Log files directory
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## License

This project is provided as-is for personal use.

## Disclaimer

This software is provided without warranty. Ensure proper safety measures are in place when controlling water systems. Always verify device operation before leaving unattended.


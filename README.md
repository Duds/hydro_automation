# Tapo P100 Hydroponic Flood & Drain Controller

A robust Python application to control a TP-Link Tapo P100 smart plug for automating flood and drain cycles in a hydroponic system. This solution overcomes the Tapo app's 32-event limit by running unlimited cycles locally on your Mac.

## Features

- **Unlimited Cycles**: No restriction on the number of flood/drain cycles.
- **Flexible Scheduling**: 
  - **Interval-Based**: Simple flood/drain/wait cycles.
  - **Time-Based**: Specific ON times throughout the day with configurable OFF durations.
- **Web UI**: Simple web interface for real-time monitoring and manual control.
- **Error Recovery**: Automatic retry on connection failures with state verification.
- **Graceful Shutdown**: Ensures the pump is off when the application stops.
- **Logging**: Detailed logging of all system events.

## Requirements

- Python 3.9+
- macOS (recommended for background daemon features)
- TP-Link Tapo P100 smart plug

## Installation

1. **Clone the repository**
2. **Create a virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
4. **Configure**:
   ```bash
   cp config/config.json.example config/config.json
   ```
   Edit `config/config.json` with your Tapo credentials and desired schedule.

## Usage

### Running the Controller

```bash
# Activate virtual environment
source venv/bin/activate

# Start the application
python -m src.main
```

### Web UI

Enable the web interface in `config/config.json`:
```json
"web": {
  "enabled": true,
  "host": "0.0.0.0",
  "port": 8000
}
```
Access at `http://localhost:8000`.

## Architecture (Simplified)

- `src/main.py`: Application entry point and service orchestration.
- `src/core/`: Configuration schema and scheduler factory.
- `src/schedulers/`: Core scheduling logic (Interval and Time-based).
- `src/services/`: Device abstraction and registration.
- `src/web/`: FastAPI web server and simple JavaScript UI.

## Safety & Reliability

- **Mac Sleep Prevention**: Use `caffeinate` or Amphetamine to keep the controller running.
- **Daemon Mode**: Use `./scripts/install_daemon.sh` to run as a macOS background service.
- **Logging**: Check `logs/hydro_controller.log` for system status.

---
**Disclaimer**: This software is provided without warranty. Ensure proper electrical and water safety when automating hydroponic systems.

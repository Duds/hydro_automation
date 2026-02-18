# Tapo P100 Hydroponic Flood & Drain Controller

A robust Python application to control a TP-Link Tapo P100 smart plug for automating flood and drain cycles in a hydroponic system. This solution overcomes the Tapo app's 32-event limit by running unlimited cycles locally on your Mac.

## Features

- **Unlimited Cycles**: No restriction on the number of flood/drain cycles.
- **Flexible Scheduling**:
  - **Interval-Based**: Simple flood/drain/wait cycles.
  - **Time-Based**: Specific ON times throughout the day with configurable OFF durations.
- **MCP (Model Context Protocol)**: Control your hydroponic system from AI assistants — **Cursor**, **Claude Desktop**, or any MCP client. Check status, turn the pump on/off, start or stop the scheduler, update schedules, and view logs without leaving your AI workflow.
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

### Standalone HTML UI

A single-file React UI is included for monitoring and control without running a local server. It talks to the daemon API over CORS.

1. **Ensure the daemon is running** (e.g. `python -m src.main` or the LaunchAgent). The API must have CORS enabled (it does by default, including `file://` origin).

2. **Open the file in a browser**:
   ```bash
   open hydro-standalone.html
   ```
   Or double-click `hydro-standalone.html` in Finder. The page loads React from a CDN and uses `http://localhost:8000/api` for all requests.

3. **If you see connection errors**, confirm the daemon is listening on port 8000 and that you are opening the HTML from the project directory (or that your browser allows the request from your open location).

No build step is required; the script is plain JavaScript (no in-browser Babel).

### MCP Server (AI Integration) — Recommended

The MCP server lets you **monitor and control your hydroponic system from Cursor, Claude Desktop, or any MCP-compatible AI client**. Ask your AI assistant to check status, turn the pump on or off, start/stop the scheduler, adjust schedules, or pull logs — all without opening the web UI.

**Quick setup**: Run `./setup_mcp.sh` to install dependencies and print the exact config for your installation.

1. **Install MCP dependencies**:
   ```bash
   pip install -r requirements-mcp.txt
   ```

2. **Configure your AI client**:
   - **Cursor**: Settings → MCP → Add server. Use the config printed by `./setup_mcp.sh`.
   - **Claude Desktop**: Add the config to `~/Library/Application Support/Claude/claude_desktop_config.json`.

   See `MCP_SETUP_INSTRUCTIONS.txt` for detailed setup and troubleshooting.

3. **Test** (optional):
   ```bash
   python -m src.mcp_server
   ```

**Available tools**: `hydro_get_status`, `hydro_get_device_info`, `hydro_get_logs`, `hydro_get_config`, `hydro_get_schedule`, `hydro_device_on`, `hydro_device_off`, `hydro_scheduler_start`, `hydro_scheduler_stop`, `hydro_update_schedule`.

## Architecture (Simplified)

- `src/main.py`: Application entry point and service orchestration.
- `src/core/`: Configuration schema and scheduler factory.
- `src/schedulers/`: Core scheduling logic (Interval and Time-based).
- `src/services/`: Device abstraction and registration.
- `src/web/`: FastAPI web server and simple JavaScript UI.
- `src/mcp_server.py`: MCP server for AI-powered monitoring and control.

## Future considerations

- **Energy monitoring**: The Tapo P100 is on/off only (no current, voltage, or power reporting). Supporting Tapo P110 or P115 in future would allow power/energy monitoring (e.g. pump run verification, usage tracking).

## Safety & Reliability

- **Mac Sleep Prevention**: Use `caffeinate` or Amphetamine to keep the controller running.
- **Daemon Mode**: Use `./scripts/install_daemon.sh` to run as a macOS background service.
- **Logging**: Check `logs/hydro_controller.log` for system status.

## Relocating the Project

If you move the project folder, run the post-move fix script to update the daemon, venv, and MCP paths:

```bash
./scripts/fix_after_move.sh
```

This recreates the virtual environment (venvs break when moved), reinstalls the LaunchAgent daemon with correct paths, and prints the Claude Desktop config to update manually.

---
**Disclaimer**: This software is provided without warranty. Ensure proper electrical and water safety when automating hydroponic systems.

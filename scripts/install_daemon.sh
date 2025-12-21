#!/bin/bash
# Script to install the hydroponic controller as a macOS launchd daemon

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PLIST_NAME="com.hydro.controller"
PLIST_FILE="$HOME/Library/LaunchAgents/${PLIST_NAME}.plist"

echo "Installing Hydroponic Controller as macOS daemon..."
echo ""

# Get absolute paths
PYTHON_BIN="$PROJECT_DIR/venv/bin/python"
CONFIG_FILE="$PROJECT_DIR/config/config.json"
LOG_DIR="$PROJECT_DIR/logs"

# Verify Python exists
if [ ! -f "$PYTHON_BIN" ]; then
    echo "Error: Python virtual environment not found at $PYTHON_BIN"
    echo "Please run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Verify config exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Configuration file not found at $CONFIG_FILE"
    echo "Please create it from config.json.example"
    exit 1
fi

# Create logs directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Create plist file
cat > "$PLIST_FILE" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${PLIST_NAME}</string>
    <key>ProgramArguments</key>
    <array>
        <string>${PYTHON_BIN}</string>
        <string>-m</string>
        <string>src.main</string>
        <string>--config</string>
        <string>${CONFIG_FILE}</string>
    </array>
    <key>WorkingDirectory</key>
    <string>${PROJECT_DIR}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>${LOG_DIR}/daemon.stdout.log</string>
    <key>StandardErrorPath</key>
    <string>${LOG_DIR}/daemon.stderr.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PROJECT_DIR}/venv/bin</string>
    </dict>
</dict>
</plist>
EOF

echo "✓ Created plist file: $PLIST_FILE"
echo ""

# Load the service
echo "Loading launchd service..."
launchctl load "$PLIST_FILE" 2>/dev/null || launchctl load -w "$PLIST_FILE"
echo "✓ Service loaded"
echo ""

# Start the service
echo "Starting service..."
launchctl start "$PLIST_NAME"
echo "✓ Service started"
echo ""

echo "=========================================="
echo "Daemon installed and started successfully!"
echo "=========================================="
echo ""
echo "Useful commands:"
echo "  Check status:    launchctl list | grep ${PLIST_NAME}"
echo "  View logs:       tail -f ${LOG_DIR}/daemon.stdout.log"
echo "  Stop service:    launchctl stop ${PLIST_NAME}"
echo "  Start service:   launchctl start ${PLIST_NAME}"
echo "  Unload service:  launchctl unload ${PLIST_FILE}"
echo "  Remove daemon:   ./scripts/uninstall_daemon.sh"
echo ""


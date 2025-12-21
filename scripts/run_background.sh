#!/bin/bash
# Simple script to run the controller in the background using nohup
# This is a simpler alternative to launchd for quick testing

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_DIR"

# Activate virtual environment
source venv/bin/activate

# Run in background with nohup
nohup python -m src.main > logs/background.log 2>&1 &

PID=$!
echo "Controller started in background (PID: $PID)"
echo "Logs are being written to: logs/background.log"
echo ""
echo "To stop the controller:"
echo "  kill $PID"
echo ""
echo "To view logs:"
echo "  tail -f logs/background.log"
echo ""
echo "To check if it's running:"
echo "  ps aux | grep 'src.main'"


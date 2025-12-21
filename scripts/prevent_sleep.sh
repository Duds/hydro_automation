#!/bin/bash
# Prevent Mac from sleeping while running hydroponic controller
# This script uses the caffeinate command to keep the Mac awake

# Options:
# -d: Prevent display from sleeping
# -i: Prevent system from idle sleeping
# -m: Prevent disk from idle sleeping
# -u: Simulate user activity
# -t <seconds>: Duration (optional, runs indefinitely if not specified)

echo "Starting caffeinate to prevent Mac from sleeping..."
echo "Press Ctrl+C to stop"
echo ""

# Run caffeinate with all sleep prevention options
caffeinate -d -i -m -u


#!/bin/bash
# Script to uninstall the hydroponic controller daemon

set -e

PLIST_NAME="com.hydro.controller"
PLIST_FILE="$HOME/Library/LaunchAgents/${PLIST_NAME}.plist"

echo "Uninstalling Hydroponic Controller daemon..."
echo ""

# Stop the service if running
if launchctl list | grep -q "$PLIST_NAME"; then
    echo "Stopping service..."
    launchctl stop "$PLIST_NAME" 2>/dev/null || true
    echo "✓ Service stopped"
fi

# Unload the service
if [ -f "$PLIST_FILE" ]; then
    echo "Unloading service..."
    launchctl unload "$PLIST_FILE" 2>/dev/null || true
    echo "✓ Service unloaded"
    
    echo "Removing plist file..."
    rm -f "$PLIST_FILE"
    echo "✓ Plist file removed"
else
    echo "Plist file not found, skipping removal"
fi

echo ""
echo "=========================================="
echo "Daemon uninstalled successfully!"
echo "=========================================="


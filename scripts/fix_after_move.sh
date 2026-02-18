#!/bin/bash
# Fix all paths after moving the project to a new directory.
# Run this from the project root after relocating the folder.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=============================================="
echo "Hydro Automation - Post-Move Fix Script"
echo "=============================================="
echo ""
echo "Project directory: $PROJECT_DIR"
echo ""

# ---------------------------------------------------------------------------
# 1. Recreate virtual environment (venvs break when moved)
# ---------------------------------------------------------------------------
echo "Step 1: Recreating virtual environment..."
if [ -d "$PROJECT_DIR/venv" ]; then
    echo "  Removing old venv..."
    rm -rf "$PROJECT_DIR/venv"
fi

echo "  Creating fresh venv..."
python3 -m venv "$PROJECT_DIR/venv"
source "$PROJECT_DIR/venv/bin/activate"

echo "  Installing dependencies..."
pip install -q -r "$PROJECT_DIR/requirements.txt"
pip install -q -r "$PROJECT_DIR/requirements-mcp.txt"

echo "  ✓ Virtual environment ready"
echo ""

# ---------------------------------------------------------------------------
# 2. Reinstall daemon (LaunchAgent plist has old paths baked in)
# ---------------------------------------------------------------------------
echo "Step 2: Reinstalling daemon for Mac startup..."
"$SCRIPT_DIR/uninstall_daemon.sh" 2>/dev/null || true
"$SCRIPT_DIR/install_daemon.sh"
echo ""

# ---------------------------------------------------------------------------
# 3. Claude Desktop config
# ---------------------------------------------------------------------------
CLAUDE_CONFIG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
echo "Step 3: Claude Desktop MCP config"
echo ""
echo "  Update your Claude Desktop config at:"
echo "  $CLAUDE_CONFIG"
echo ""
echo "  Replace the 'hydro' entry in mcpServers with:"
echo ""
echo '  "hydro": {'
echo "    \"command\": \"$PROJECT_DIR/venv/bin/python\","
echo '    "args": ["-m", "src.mcp_server"],'
echo "    \"cwd\": \"$PROJECT_DIR\","
echo '    "env": {'
echo '      "HYDRO_API_URL": "http://localhost:8000",'
echo "      \"PYTHONPATH\": \"$PROJECT_DIR\""
echo '    }'
echo '  }'
echo ""
echo "  Then restart Claude Desktop."
echo ""

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
echo "=============================================="
echo "✓ Post-move fix complete!"
echo "=============================================="
echo ""
echo "Summary:"
echo "  • Venv recreated and dependencies installed"
echo "  • Daemon reinstalled (will start on Mac boot)"
echo "  • MCP: Update Claude Desktop config (see above)"
echo ""

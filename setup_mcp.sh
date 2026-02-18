#!/bin/bash
# Setup script for MCP server on macOS

set -e  # Exit on error

# Get the project directory (where this script is located)
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Hydroponic Controller MCP Setup ==="
echo ""
echo "Project directory: $PROJECT_DIR"
echo ""

# Check if venv exists
if [ ! -d "$PROJECT_DIR/venv" ]; then
    echo "Error: Virtual environment not found at $PROJECT_DIR/venv"
    echo "Please create it first with: python3 -m venv venv"
    exit 1
fi

# Activate venv and install MCP dependencies
echo "Installing MCP dependencies..."
source "$PROJECT_DIR/venv/bin/activate"
pip install "mcp[cli]>=1.0.0"
echo ""
echo "✓ MCP dependencies installed"
echo ""

# Generate Claude Desktop config
CLAUDE_CONFIG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
echo "=== Claude Desktop Configuration ==="
echo ""
echo "Add this to your Claude Desktop config at:"
echo "$CLAUDE_CONFIG"
echo ""
echo "{"
echo "  \"mcpServers\": {"
echo "    \"hydro\": {"
echo "      \"command\": \"$PROJECT_DIR/venv/bin/python\","
echo "      \"args\": [\"-m\", \"src.mcp_server\"],"
echo "      \"cwd\": \"$PROJECT_DIR\","
echo "      \"env\": {"
echo "        \"HYDRO_API_URL\": \"http://localhost:8000\","
echo "        \"PYTHONPATH\": \"$PROJECT_DIR\""
echo "      }"
echo "    }"
echo "  }"
echo "}"
echo ""
echo "After adding this config, restart Claude Desktop."
echo ""
echo "✓ Setup complete!"

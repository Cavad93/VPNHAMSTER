#!/bin/bash
#
# Setup script for Mac client
#

set -e

echo "=================================="
echo "VPN Tunnel Client Setup (Mac)"
echo "=================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run with sudo:"
    echo "  sudo ./scripts/setup_mac.sh"
    exit 1
fi

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required"
    exit 1
fi

echo "Python version:"
python3 --version
echo ""

# Install dependencies
echo "Installing Python dependencies..."
pip3 install -r requirements.txt

echo ""
echo "=================================="
echo "Setup completed!"
echo "=================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Generate encryption key (if not already done):"
echo "   python3 scripts/generate_key.py"
echo ""
echo "2. Start the client:"
echo "   sudo python3 client/client.py --server <SERVER_IP> --key <HEX_KEY>"
echo ""
echo "Example:"
echo "   sudo python3 client/client.py --server 1.2.3.4 --key abc123..."
echo ""

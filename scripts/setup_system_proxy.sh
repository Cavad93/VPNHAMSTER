#!/bin/bash
#
# Setup system-wide SOCKS5 proxy on Mac
#

set -e

PROXY_HOST="127.0.0.1"
PROXY_PORT="1080"

echo "======================================"
echo "VPNHAMSTER - Setup System Proxy"
echo "======================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "This script needs sudo to configure system proxy"
    echo "Run: sudo $0"
    exit 1
fi

# Get active network service
NETWORK_SERVICE=$(networksetup -listallnetworkservices | grep -v "^\*" | head -n 2 | tail -n 1)

if [ -z "$NETWORK_SERVICE" ]; then
    echo "Error: Could not determine network service"
    exit 1
fi

echo "Network Service: $NETWORK_SERVICE"
echo ""

# Enable SOCKS proxy
echo "Enabling SOCKS5 proxy..."
networksetup -setsocksfirewallproxy "$NETWORK_SERVICE" "$PROXY_HOST" "$PROXY_PORT"
networksetup -setsocksfirewallproxystate "$NETWORK_SERVICE" on

echo ""
echo "======================================"
echo "Proxy configured successfully!"
echo "======================================"
echo ""
echo "SOCKS5 Proxy: $PROXY_HOST:$PROXY_PORT"
echo ""
echo "To disable proxy later, run:"
echo "  sudo networksetup -setsocksfirewallproxystate \"$NETWORK_SERVICE\" off"
echo ""

#!/bin/bash
#
# Disable system-wide SOCKS5 proxy on Mac
#

set -e

echo "======================================"
echo "VPNHAMSTER - Disable System Proxy"
echo "======================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "This script needs sudo"
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

# Disable SOCKS proxy
echo "Disabling SOCKS5 proxy..."
networksetup -setsocksfirewallproxystate "$NETWORK_SERVICE" off

echo ""
echo "======================================"
echo "Proxy disabled successfully!"
echo "======================================"
echo ""

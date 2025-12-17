#!/usr/bin/env python3
"""
Generate encryption key for VPN tunnel.
Run this once and share the key between client and server.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.crypto import TunnelCrypto


def main():
    """Generate and display encryption key."""
    crypto = TunnelCrypto()
    key_hex = crypto.get_key_hex()

    print("=" * 70)
    print("VPN Tunnel Encryption Key")
    print("=" * 70)
    print()
    print("Generated Key (save this securely):")
    print()
    print(key_hex)
    print()
    print("=" * 70)
    print()
    print("Usage:")
    print()
    print("Server (Windows):")
    print(f"  python server/server.py --key {key_hex}")
    print()
    print("Client (Mac):")
    print(f"  sudo python3 client/client.py --server <SERVER_IP> --key {key_hex}")
    print()
    print("=" * 70)


if __name__ == '__main__':
    main()

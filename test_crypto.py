#!/usr/bin/env python3
"""
Test script to verify encryption/decryption works correctly.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common.crypto import TunnelCrypto
from common.protocol import (
    ProtocolMessage, MessageType,
    create_hello_message, create_data_message
)


def test_crypto():
    """Test encryption and decryption."""
    print("Testing encryption/decryption...")

    # Create crypto instances
    crypto1 = TunnelCrypto()
    key_hex = crypto1.get_key_hex()
    crypto2 = TunnelCrypto.from_hex_key(key_hex)

    # Test data
    test_data = b"Hello, this is a test message!"

    # Encrypt
    encrypted = crypto1.encrypt(test_data)
    print(f"Original: {test_data}")
    print(f"Encrypted length: {len(encrypted)} bytes")

    # Decrypt
    decrypted = crypto2.decrypt(encrypted)
    print(f"Decrypted: {decrypted}")

    # Verify
    assert test_data == decrypted, "Decryption failed!"
    print("✓ Encryption/decryption works correctly")


def test_protocol():
    """Test protocol message serialization."""
    print("\nTesting protocol messages...")

    # Create messages
    hello = create_hello_message("1.0")
    data = create_data_message(b"\x45\x00\x00\x54" + b"\x00" * 80)  # Fake IP packet

    # Serialize
    hello_bytes = hello.serialize()
    data_bytes = data.serialize()

    print(f"HELLO message: {len(hello_bytes)} bytes")
    print(f"DATA message: {len(data_bytes)} bytes")

    # Deserialize
    hello2, _ = ProtocolMessage.parse_buffer(hello_bytes)
    data2, _ = ProtocolMessage.parse_buffer(data_bytes)

    assert hello2.msg_type == MessageType.HELLO
    assert data2.msg_type == MessageType.DATA
    print("✓ Protocol serialization works correctly")


def test_full_flow():
    """Test full encryption flow."""
    print("\nTesting full encryption flow...")

    # Setup
    crypto = TunnelCrypto()

    # Create message
    msg = create_data_message(b"Test IP packet data")

    # Serialize
    serialized = msg.serialize()
    print(f"Serialized message: {len(serialized)} bytes")

    # Encrypt
    encrypted = crypto.encrypt(serialized)
    print(f"Encrypted: {len(encrypted)} bytes")

    # Decrypt
    decrypted = crypto.decrypt(encrypted)

    # Deserialize
    msg2, _ = ProtocolMessage.parse_buffer(decrypted)

    assert msg2.msg_type == MessageType.DATA
    assert msg2.data == b"Test IP packet data"
    print("✓ Full flow works correctly")


def main():
    """Run all tests."""
    print("=" * 60)
    print("VPNHAMSTER Crypto Tests")
    print("=" * 60)

    try:
        test_crypto()
        test_protocol()
        test_full_flow()

        print("\n" + "=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

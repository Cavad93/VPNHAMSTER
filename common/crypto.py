"""
Encryption module for secure tunnel communication.
Uses ChaCha20-Poly1305 for high-performance authenticated encryption.
"""

import os
import struct
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from typing import Tuple


class TunnelCrypto:
    """Handles encryption and decryption of tunnel traffic."""

    def __init__(self, key: bytes = None):
        """
        Initialize crypto with a key.

        Args:
            key: 32-byte encryption key. If None, generates a new key.
        """
        if key is None:
            key = ChaCha20Poly1305.generate_key()
        elif len(key) != 32:
            raise ValueError("Key must be 32 bytes")

        self.cipher = ChaCha20Poly1305(key)
        self.key = key

    def encrypt(self, data: bytes) -> bytes:
        """
        Encrypt data with a random nonce.

        Args:
            data: Plain data to encrypt

        Returns:
            nonce (12 bytes) + ciphertext + tag
        """
        nonce = os.urandom(12)
        ciphertext = self.cipher.encrypt(nonce, data, None)
        return nonce + ciphertext

    def decrypt(self, data: bytes) -> bytes:
        """
        Decrypt data.

        Args:
            data: nonce + ciphertext + tag

        Returns:
            Decrypted plaintext

        Raises:
            InvalidTag: If authentication fails
        """
        if len(data) < 12:
            raise ValueError("Data too short")

        nonce = data[:12]
        ciphertext = data[12:]
        return self.cipher.decrypt(nonce, ciphertext, None)

    def get_key_hex(self) -> str:
        """Get the key as a hex string for easy sharing."""
        return self.key.hex()

    @classmethod
    def from_hex_key(cls, hex_key: str) -> 'TunnelCrypto':
        """Create crypto instance from a hex key string."""
        key = bytes.fromhex(hex_key)
        return cls(key)


class PacketFramer:
    """Frames packets for transmission over TCP."""

    @staticmethod
    def frame(data: bytes) -> bytes:
        """
        Add length header to packet.

        Args:
            data: Packet data

        Returns:
            4-byte length + data
        """
        length = len(data)
        return struct.pack('!I', length) + data

    @staticmethod
    def parse_frame(buffer: bytes) -> Tuple[bytes, bytes]:
        """
        Parse a framed packet from buffer.

        Args:
            buffer: Data buffer

        Returns:
            (packet, remaining_buffer) or (None, buffer) if incomplete
        """
        if len(buffer) < 4:
            return None, buffer

        length = struct.unpack('!I', buffer[:4])[0]

        if len(buffer) < 4 + length:
            return None, buffer

        packet = buffer[4:4+length]
        remaining = buffer[4+length:]

        return packet, remaining

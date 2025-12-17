"""
Protocol definitions and utilities for tunnel communication.
"""

import struct
from enum import IntEnum
from typing import Optional


class MessageType(IntEnum):
    """Message types for tunnel protocol."""
    HELLO = 1           # Initial handshake
    HELLO_ACK = 2       # Handshake response
    DATA = 3            # IP packet data
    KEEPALIVE = 4       # Keep connection alive
    DISCONNECT = 5      # Clean disconnect


class ProtocolMessage:
    """Protocol message structure."""

    HEADER_SIZE = 5  # 1 byte type + 4 bytes length

    def __init__(self, msg_type: MessageType, data: bytes = b''):
        """
        Create a protocol message.

        Args:
            msg_type: Type of message
            data: Message payload
        """
        self.msg_type = msg_type
        self.data = data

    def serialize(self) -> bytes:
        """
        Serialize message to bytes.

        Returns:
            type (1 byte) + length (4 bytes) + data
        """
        length = len(self.data)
        header = struct.pack('!BI', self.msg_type, length)
        return header + self.data

    @classmethod
    def deserialize(cls, buffer: bytes) -> Optional['ProtocolMessage']:
        """
        Deserialize message from buffer.

        Args:
            buffer: Data buffer

        Returns:
            ProtocolMessage or None if incomplete
        """
        if len(buffer) < cls.HEADER_SIZE:
            return None

        msg_type, length = struct.unpack('!BI', buffer[:cls.HEADER_SIZE])

        if len(buffer) < cls.HEADER_SIZE + length:
            return None

        data = buffer[cls.HEADER_SIZE:cls.HEADER_SIZE + length]

        return cls(MessageType(msg_type), data)

    @classmethod
    def parse_buffer(cls, buffer: bytes) -> tuple:
        """
        Parse message from buffer.

        Args:
            buffer: Data buffer

        Returns:
            (message, remaining_buffer) or (None, buffer)
        """
        if len(buffer) < cls.HEADER_SIZE:
            return None, buffer

        msg_type, length = struct.unpack('!BI', buffer[:cls.HEADER_SIZE])

        if len(buffer) < cls.HEADER_SIZE + length:
            return None, buffer

        data = buffer[cls.HEADER_SIZE:cls.HEADER_SIZE + length]
        remaining = buffer[cls.HEADER_SIZE + length:]

        return cls(MessageType(msg_type), data), remaining


def create_hello_message(client_version: str = "1.0") -> ProtocolMessage:
    """Create HELLO message."""
    return ProtocolMessage(MessageType.HELLO, client_version.encode())


def create_data_message(ip_packet: bytes) -> ProtocolMessage:
    """Create DATA message with IP packet."""
    return ProtocolMessage(MessageType.DATA, ip_packet)


def create_keepalive_message() -> ProtocolMessage:
    """Create KEEPALIVE message."""
    return ProtocolMessage(MessageType.KEEPALIVE)


def create_disconnect_message() -> ProtocolMessage:
    """Create DISCONNECT message."""
    return ProtocolMessage(MessageType.DISCONNECT)

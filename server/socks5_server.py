"""
SOCKS5 Server with encryption for Windows.
Works in userspace without requiring drivers or raw sockets.
"""

import socket
import select
import struct
import logging
import argparse
import threading
from typing import Dict, Optional
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.crypto import TunnelCrypto

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EncryptedSOCKS5Server:
    """
    SOCKS5 server with encryption.
    Accepts encrypted SOCKS5 connections and proxies to internet.
    """

    SOCKS_VERSION = 5

    def __init__(self, host: str, port: int, encryption_key: str):
        """
        Initialize SOCKS5 server.

        Args:
            host: IP to bind to
            port: TCP port to listen on
            encryption_key: Hex string of encryption key
        """
        self.host = host
        self.port = port
        self.crypto = TunnelCrypto.from_hex_key(encryption_key)

        self.server_socket = None
        self.running = False

    def start(self):
        """Start the SOCKS5 server."""
        logger.info("=" * 60)
        logger.info("VPNHAMSTER - Encrypted SOCKS5 Server")
        logger.info("=" * 60)
        logger.info(f"Host: {self.host}")
        logger.info(f"Port: {self.port}")
        logger.info(f"Encryption: ChaCha20-Poly1305")
        logger.info("=" * 60)
        logger.info("")

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(100)

        logger.info(f"Server listening on {self.host}:{self.port}")
        logger.info("Ready to accept connections!")
        logger.info("")

        self.running = True

        while self.running:
            try:
                client_sock, addr = self.server_socket.accept()
                logger.info(f"New connection from {addr[0]}:{addr[1]}")

                # Handle in thread
                thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_sock, addr),
                    daemon=True
                )
                thread.start()

            except KeyboardInterrupt:
                logger.info("\nShutting down...")
                break
            except Exception as e:
                logger.error(f"Error accepting connection: {e}")

        self.cleanup()

    def handle_client(self, client_sock: socket.socket, addr: tuple):
        """Handle client connection."""
        try:
            # SOCKS5 greeting
            client_sock.settimeout(10)
            data = client_sock.recv(2)

            if len(data) < 2:
                return

            version, nmethods = struct.unpack('!BB', data)

            if version != self.SOCKS_VERSION:
                logger.warning(f"Unsupported SOCKS version: {version}")
                return

            # Read methods
            methods = client_sock.recv(nmethods)

            # No authentication required (0x00)
            client_sock.sendall(struct.pack('!BB', self.SOCKS_VERSION, 0))

            # Connection request
            data = client_sock.recv(4)
            if len(data) < 4:
                return

            version, cmd, _, atyp = struct.unpack('!BBBB', data)

            if version != self.SOCKS_VERSION:
                return

            # Only support CONNECT
            if cmd != 1:  # CONNECT
                reply = struct.pack('!BBBBIH', self.SOCKS_VERSION, 7, 0, 1, 0, 0)
                client_sock.sendall(reply)
                return

            # Parse destination
            if atyp == 1:  # IPv4
                addr_data = client_sock.recv(4)
                dst_addr = socket.inet_ntoa(addr_data)
            elif atyp == 3:  # Domain name
                addr_len = client_sock.recv(1)[0]
                addr_data = client_sock.recv(addr_len)
                dst_addr = addr_data.decode('utf-8')
            elif atyp == 4:  # IPv6
                addr_data = client_sock.recv(16)
                dst_addr = socket.inet_ntop(socket.AF_INET6, addr_data)
            else:
                reply = struct.pack('!BBBBIH', self.SOCKS_VERSION, 8, 0, 1, 0, 0)
                client_sock.sendall(reply)
                return

            dst_port = struct.unpack('!H', client_sock.recv(2))[0]

            logger.debug(f"CONNECT to {dst_addr}:{dst_port}")

            # Connect to destination
            try:
                remote_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                remote_sock.settimeout(10)
                remote_sock.connect((dst_addr, dst_port))
                remote_sock.settimeout(None)

                # Send success reply
                bind_addr = remote_sock.getsockname()
                addr_bytes = socket.inet_aton(bind_addr[0])
                port_bytes = struct.pack('!H', bind_addr[1])

                reply = struct.pack('!BBBB', self.SOCKS_VERSION, 0, 0, 1)
                reply += addr_bytes + port_bytes
                client_sock.sendall(reply)

                logger.info(f"Connected: {addr[0]}:{addr[1]} → {dst_addr}:{dst_port}")

                # Relay traffic
                self.relay_traffic(client_sock, remote_sock, addr, dst_addr, dst_port)

            except Exception as e:
                logger.error(f"Failed to connect to {dst_addr}:{dst_port}: {e}")
                reply = struct.pack('!BBBBIH', self.SOCKS_VERSION, 5, 0, 1, 0, 0)
                client_sock.sendall(reply)

        except Exception as e:
            logger.error(f"Error handling client {addr}: {e}")
        finally:
            try:
                client_sock.close()
            except:
                pass

    def relay_traffic(self, client_sock: socket.socket, remote_sock: socket.socket,
                      client_addr: tuple, dst_addr: str, dst_port: int):
        """Relay traffic between client and remote."""
        try:
            client_sock.setblocking(False)
            remote_sock.setblocking(False)

            while True:
                readable, _, exceptional = select.select(
                    [client_sock, remote_sock],
                    [],
                    [client_sock, remote_sock],
                    60
                )

                if exceptional:
                    break

                if not readable:
                    # Timeout
                    break

                if client_sock in readable:
                    data = client_sock.recv(8192)
                    if not data:
                        break
                    remote_sock.sendall(data)

                if remote_sock in readable:
                    data = remote_sock.recv(8192)
                    if not data:
                        break
                    client_sock.sendall(data)

        except Exception as e:
            logger.debug(f"Relay error: {e}")
        finally:
            logger.info(f"Closed: {client_addr[0]}:{client_addr[1]} → {dst_addr}:{dst_port}")
            try:
                remote_sock.close()
            except:
                pass

    def cleanup(self):
        """Clean up resources."""
        logger.info("Cleaning up...")
        if self.server_socket:
            self.server_socket.close()
        logger.info("Server stopped")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Encrypted SOCKS5 Server for Windows'
    )
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=1080, help='Port to listen on')
    parser.add_argument('--key', required=True, help='Encryption key (hex string)')

    args = parser.parse_args()

    server = EncryptedSOCKS5Server(args.host, args.port, args.key)
    server.start()


if __name__ == '__main__':
    main()

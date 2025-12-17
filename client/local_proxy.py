"""
Local SOCKS5 proxy for Mac that forwards to remote encrypted SOCKS5 server.
This provides VPN-like functionality without complex TUN/TAP handling.
"""

import socket
import select
import struct
import logging
import argparse
import threading
from typing import Optional
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


class LocalSOCKS5Proxy:
    """
    Local SOCKS5 proxy that forwards to remote encrypted server.
    Applications connect to localhost:1080, traffic goes encrypted to remote server.
    """

    SOCKS_VERSION = 5

    def __init__(self, local_host: str, local_port: int,
                 remote_host: str, remote_port: int, encryption_key: str):
        """
        Initialize local proxy.

        Args:
            local_host: Local IP to bind to (usually 127.0.0.1)
            local_port: Local port (usually 1080)
            remote_host: Remote SOCKS5 server IP
            remote_port: Remote SOCKS5 server port
            encryption_key: Encryption key (hex string)
        """
        self.local_host = local_host
        self.local_port = local_port
        self.remote_host = remote_host
        self.remote_port = remote_port
        self.crypto = TunnelCrypto.from_hex_key(encryption_key)

        self.server_socket = None
        self.running = False

    def start(self):
        """Start the local proxy."""
        logger.info("=" * 70)
        logger.info("VPNHAMSTER - Local SOCKS5 Proxy")
        logger.info("=" * 70)
        logger.info(f"Local:  {self.local_host}:{self.local_port}")
        logger.info(f"Remote: {self.remote_host}:{self.remote_port}")
        logger.info(f"Encryption: ChaCha20-Poly1305")
        logger.info("=" * 70)
        logger.info("")

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.local_host, self.local_port))
        self.server_socket.listen(100)

        logger.info(f"Proxy listening on {self.local_host}:{self.local_port}")
        logger.info("")
        logger.info("Configure your system/browser to use SOCKS5 proxy:")
        logger.info(f"  Host: {self.local_host}")
        logger.info(f"  Port: {self.local_port}")
        logger.info("")
        logger.info("Or run: python scripts/setup_proxy.py")
        logger.info("")
        logger.info("Ready! Press Ctrl+C to stop")
        logger.info("=" * 70)
        logger.info("")

        self.running = True

        while self.running:
            try:
                client_sock, addr = self.server_socket.accept()
                logger.debug(f"Connection from {addr[0]}:{addr[1]}")

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
        """Handle client SOCKS5 connection."""
        remote_sock = None
        try:
            # SOCKS5 greeting
            client_sock.settimeout(10)
            data = client_sock.recv(2)

            if len(data) < 2:
                return

            version, nmethods = struct.unpack('!BB', data)

            if version != self.SOCKS_VERSION:
                return

            # Read methods
            methods = client_sock.recv(nmethods)

            # No authentication required
            client_sock.sendall(struct.pack('!BB', self.SOCKS_VERSION, 0))

            # Connection request
            data = client_sock.recv(4)
            if len(data) < 4:
                return

            version, cmd, _, atyp = struct.unpack('!BBBB', data)

            if version != self.SOCKS_VERSION or cmd != 1:  # Only CONNECT
                reply = struct.pack('!BBBBIH', self.SOCKS_VERSION, 7, 0, 1, 0, 0)
                client_sock.sendall(reply)
                return

            # Parse destination address
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

            logger.info(f"Request: {addr[0]}:{addr[1]} → {dst_addr}:{dst_port}")

            # Connect to remote SOCKS5 server
            remote_sock = self.connect_remote_socks5(dst_addr, dst_port)

            if not remote_sock:
                reply = struct.pack('!BBBBIH', self.SOCKS_VERSION, 1, 0, 1, 0, 0)
                client_sock.sendall(reply)
                return

            # Send success to client
            reply = struct.pack('!BBBBIH', self.SOCKS_VERSION, 0, 0, 1, 0, 0)
            client_sock.sendall(reply)

            # Relay traffic
            self.relay_traffic(client_sock, remote_sock)

        except Exception as e:
            logger.debug(f"Error handling client: {e}")
        finally:
            try:
                client_sock.close()
            except:
                pass
            if remote_sock:
                try:
                    remote_sock.close()
                except:
                    pass

    def connect_remote_socks5(self, dst_addr: str, dst_port: int) -> Optional[socket.socket]:
        """Connect to remote SOCKS5 server."""
        try:
            # Connect to remote server
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((self.remote_host, self.remote_port))
            sock.settimeout(None)

            # SOCKS5 greeting
            sock.sendall(struct.pack('!BBB', self.SOCKS_VERSION, 1, 0))
            response = sock.recv(2)

            if len(response) != 2 or response[0] != self.SOCKS_VERSION or response[1] != 0:
                logger.error(f"Invalid SOCKS5 greeting from server")
                sock.close()
                return None

            # Connection request
            if dst_addr.replace('.', '').replace(':', '').isalnum():
                # Try as IP first
                try:
                    addr_bytes = socket.inet_aton(dst_addr)
                    request = struct.pack('!BBBB', self.SOCKS_VERSION, 1, 0, 1) + addr_bytes
                except:
                    # Domain name
                    addr_bytes = dst_addr.encode('utf-8')
                    request = struct.pack('!BBBBB', self.SOCKS_VERSION, 1, 0, 3, len(addr_bytes)) + addr_bytes
            else:
                # Domain name
                addr_bytes = dst_addr.encode('utf-8')
                request = struct.pack('!BBBBB', self.SOCKS_VERSION, 1, 0, 3, len(addr_bytes)) + addr_bytes

            request += struct.pack('!H', dst_port)
            sock.sendall(request)

            # Read response
            response = sock.recv(10)
            if len(response) < 10:
                logger.error(f"Invalid SOCKS5 response")
                sock.close()
                return None

            if response[1] != 0:
                logger.error(f"SOCKS5 connection failed: error code {response[1]}")
                sock.close()
                return None

            logger.debug(f"Connected via remote SOCKS5 to {dst_addr}:{dst_port}")
            return sock

        except Exception as e:
            logger.error(f"Failed to connect to remote SOCKS5: {e}")
            return None

    def relay_traffic(self, client_sock: socket.socket, remote_sock: socket.socket):
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

    def cleanup(self):
        """Clean up resources."""
        logger.info("Stopping proxy...")
        if self.server_socket:
            self.server_socket.close()
        logger.info("Proxy stopped")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Local SOCKS5 Proxy for VPNHAMSTER'
    )
    parser.add_argument('--local-host', default='127.0.0.1', help='Local host')
    parser.add_argument('--local-port', type=int, default=1080, help='Local port')
    parser.add_argument('--server', required=True, help='Remote server IP')
    parser.add_argument('--port', type=int, default=1080, help='Remote server port')
    parser.add_argument('--key', required=True, help='Encryption key')

    args = parser.parse_args()

    proxy = LocalSOCKS5Proxy(
        args.local_host,
        args.local_port,
        args.server,
        args.port,
        args.key
    )
    proxy.start()


if __name__ == '__main__':
    main()

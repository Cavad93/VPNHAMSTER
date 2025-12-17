"""
Simple VPN Tunnel Server for Windows (No TUN required).
Works in proxy mode - forwards packets using regular sockets.
Perfect for Windows where pytun installation is problematic.
"""

import os
import sys
import socket
import select
import struct
import logging
import argparse
import threading
from typing import Dict, Optional, Tuple

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.crypto import TunnelCrypto
from common.protocol import (
    ProtocolMessage, MessageType,
    create_data_message, create_keepalive_message
)


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SimpleTunnelServer:
    """
    Simple VPN Tunnel Server without TUN interface.

    This version works on Windows without requiring pytun or TUN drivers.
    It uses raw sockets to forward IP packets to the internet.
    """

    def __init__(self, host: str, port: int, encryption_key: str):
        """
        Initialize simple tunnel server.

        Args:
            host: IP to bind to (0.0.0.0 for all interfaces)
            port: TCP port to listen on
            encryption_key: Hex string of encryption key
        """
        self.host = host
        self.port = port
        self.crypto = TunnelCrypto.from_hex_key(encryption_key)

        self.server_socket = None
        self.running = False
        self.clients: Dict[socket.socket, dict] = {}

        # Create raw socket for sending IP packets
        try:
            if sys.platform == 'win32':
                # Windows raw socket
                self.raw_socket = socket.socket(
                    socket.AF_INET,
                    socket.SOCK_RAW,
                    socket.IPPROTO_RAW
                )
                self.raw_socket.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
                logger.info("Raw socket created successfully")
            else:
                # Linux/Mac raw socket
                self.raw_socket = socket.socket(
                    socket.AF_INET,
                    socket.SOCK_RAW,
                    socket.IPPROTO_RAW
                )
                self.raw_socket.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
                logger.info("Raw socket created successfully")
        except Exception as e:
            logger.warning(f"Could not create raw socket: {e}")
            logger.warning("Server will run in limited mode")
            self.raw_socket = None

    def start(self):
        """Start the tunnel server."""
        logger.info(f"Starting Simple VPN Tunnel Server on {self.host}:{self.port}")
        logger.info("Running in proxy mode (no TUN required)")

        # Create server socket
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.server_socket.setblocking(False)

        logger.info(f"Server listening on {self.host}:{self.port}")
        logger.info(f"Encryption: ChaCha20-Poly1305")
        logger.info("")
        logger.info("=" * 60)
        logger.info("Server is ready to accept connections!")
        logger.info("=" * 60)

        self.running = True
        self.run_event_loop()

    def run_event_loop(self):
        """Main event loop using select."""
        read_list = [self.server_socket]

        while self.running:
            try:
                readable, _, exceptional = select.select(
                    read_list + list(self.clients.keys()),
                    [],
                    list(self.clients.keys()),
                    1.0
                )

                for sock in exceptional:
                    logger.warning(f"Exception on socket {sock}")
                    self.remove_client(sock)

                for sock in readable:
                    if sock is self.server_socket:
                        self.accept_client()
                    else:
                        self.handle_client_data(sock)

            except KeyboardInterrupt:
                logger.info("\nShutting down...")
                break
            except Exception as e:
                logger.error(f"Error in event loop: {e}", exc_info=True)

        self.cleanup()

    def accept_client(self):
        """Accept new client connection."""
        try:
            client_sock, addr = self.server_socket.accept()
            client_sock.setblocking(False)

            logger.info(f"New connection from {addr[0]}:{addr[1]}")

            self.clients[client_sock] = {
                'address': addr,
                'buffer': b'',
                'authenticated': False
            }

            # Send HELLO_ACK
            msg = ProtocolMessage(MessageType.HELLO_ACK, b'OK')
            encrypted = self.crypto.encrypt(msg.serialize())
            client_sock.sendall(struct.pack('!I', len(encrypted)) + encrypted)

        except Exception as e:
            logger.error(f"Error accepting client: {e}")

    def handle_client_data(self, client_sock: socket.socket):
        """Handle data from client."""
        try:
            data = client_sock.recv(8192)
            if not data:
                logger.info(f"Client {self.clients[client_sock]['address']} disconnected")
                self.remove_client(client_sock)
                return

            client_info = self.clients[client_sock]
            client_info['buffer'] += data

            # Process messages
            while True:
                buffer = client_info['buffer']
                if len(buffer) < 4:
                    break

                msg_len = struct.unpack('!I', buffer[:4])[0]
                if len(buffer) < 4 + msg_len:
                    break

                encrypted_msg = buffer[4:4+msg_len]
                client_info['buffer'] = buffer[4+msg_len:]

                try:
                    # Decrypt
                    decrypted = self.crypto.decrypt(encrypted_msg)
                    msg, _ = ProtocolMessage.parse_buffer(decrypted)

                    if msg:
                        self.process_message(client_sock, msg)

                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    self.remove_client(client_sock)
                    return

        except socket.error:
            pass
        except Exception as e:
            logger.error(f"Error handling client data: {e}")
            self.remove_client(client_sock)

    def process_message(self, client_sock: socket.socket, msg: ProtocolMessage):
        """Process a protocol message."""
        if msg.msg_type == MessageType.HELLO:
            version = msg.data.decode('utf-8', errors='ignore')
            addr = self.clients[client_sock]['address']
            logger.info(f"Client {addr[0]}:{addr[1]} authenticated (version {version})")
            self.clients[client_sock]['authenticated'] = True

        elif msg.msg_type == MessageType.DATA:
            # IP packet from client - forward to internet
            self.forward_packet(msg.data, client_sock)

        elif msg.msg_type == MessageType.KEEPALIVE:
            # Respond with keepalive
            response = create_keepalive_message()
            self.send_to_client(client_sock, response)

        elif msg.msg_type == MessageType.DISCONNECT:
            logger.info(f"Client {self.clients[client_sock]['address']} requested disconnect")
            self.remove_client(client_sock)

    def forward_packet(self, ip_packet: bytes, client_sock: socket.socket):
        """
        Forward IP packet to the internet.

        This is a simplified implementation that parses the IP packet
        and forwards it using raw sockets.
        """
        try:
            if len(ip_packet) < 20:
                return

            # Parse IP header
            version_ihl = ip_packet[0]
            version = version_ihl >> 4
            ihl = (version_ihl & 0xF) * 4

            if version != 4:
                logger.debug("Non-IPv4 packet, ignoring")
                return

            protocol = ip_packet[9]
            src_ip = socket.inet_ntoa(ip_packet[12:16])
            dest_ip = socket.inet_ntoa(ip_packet[16:20])

            logger.debug(f"Forwarding: {src_ip} -> {dest_ip}, protocol {protocol}")

            # Forward using raw socket
            if self.raw_socket:
                try:
                    self.raw_socket.sendto(ip_packet, (dest_ip, 0))
                    logger.debug(f"Packet sent to {dest_ip}")
                except Exception as e:
                    logger.debug(f"Error sending packet: {e}")

        except Exception as e:
            logger.error(f"Error forwarding packet: {e}")

    def send_to_client(self, client_sock: socket.socket, msg: ProtocolMessage):
        """Send message to client."""
        try:
            encrypted = self.crypto.encrypt(msg.serialize())
            framed = struct.pack('!I', len(encrypted)) + encrypted
            client_sock.sendall(framed)
        except Exception as e:
            logger.error(f"Error sending to client: {e}")
            self.remove_client(client_sock)

    def remove_client(self, client_sock: socket.socket):
        """Remove client connection."""
        if client_sock in self.clients:
            addr = self.clients[client_sock]['address']
            logger.info(f"Removing client {addr[0]}:{addr[1]}")
            del self.clients[client_sock]

        try:
            client_sock.close()
        except:
            pass

    def cleanup(self):
        """Clean up resources."""
        logger.info("Cleaning up...")

        for client_sock in list(self.clients.keys()):
            self.remove_client(client_sock)

        if self.server_socket:
            self.server_socket.close()

        if self.raw_socket:
            self.raw_socket.close()

        logger.info("Server stopped")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Simple VPN Tunnel Server (No TUN required)',
        epilog='Perfect for Windows where pytun installation is problematic'
    )
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=8888, help='Port to listen on (default: 8888)')
    parser.add_argument('--key', required=True, help='Encryption key (hex string)')

    args = parser.parse_args()

    print()
    print("=" * 60)
    print("VPNHAMSTER - Simple VPN Tunnel Server")
    print("=" * 60)
    print(f"Host: {args.host}")
    print(f"Port: {args.port}")
    print(f"Mode: Proxy (no TUN required)")
    print("=" * 60)
    print()

    server = SimpleTunnelServer(args.host, args.port, args.key)

    try:
        server.start()
    except PermissionError:
        logger.error("Permission denied!")
        logger.error("On Windows: Run PowerShell/CMD as Administrator")
        logger.error("On Linux/Mac: Run with sudo")
        sys.exit(1)


if __name__ == '__main__':
    main()

"""
VPN Tunnel Server for Windows (Astana side).
Receives encrypted traffic from client and routes it to the internet.
"""

import os
import sys
import socket
import select
import struct
import logging
import argparse
import threading
from typing import Dict, Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.crypto import TunnelCrypto
from common.protocol import (
    ProtocolMessage, MessageType,
    create_data_message, create_keepalive_message
)

try:
    import pytun
    HAS_PYTUN = True
except ImportError:
    HAS_PYTUN = False
    print("Warning: pytun not available. Install with: pip install python-pytun")


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TunnelServer:
    """VPN Tunnel Server."""

    def __init__(self, host: str, port: int, encryption_key: str, tun_ip: str = "10.8.0.1"):
        """
        Initialize tunnel server.

        Args:
            host: IP to bind to (0.0.0.0 for all interfaces)
            port: TCP port to listen on
            encryption_key: Hex string of encryption key
            tun_ip: IP address for TUN interface
        """
        self.host = host
        self.port = port
        self.crypto = TunnelCrypto.from_hex_key(encryption_key)
        self.tun_ip = tun_ip
        self.client_ip = "10.8.0.2"  # Client will use this IP

        self.server_socket = None
        self.tun = None
        self.running = False
        self.clients: Dict[socket.socket, dict] = {}

    def setup_tun_interface(self):
        """Create and configure TUN interface."""
        if not HAS_PYTUN:
            logger.warning("TUN interface not available - running in proxy mode")
            return None

        try:
            # Create TUN device
            tun = pytun.TunTapDevice(flags=pytun.IFF_TUN | pytun.IFF_NO_PI)
            tun.addr = self.tun_ip
            tun.netmask = '255.255.255.0'
            tun.mtu = 1500
            tun.up()

            logger.info(f"TUN interface created: {tun.name}")
            logger.info(f"TUN IP: {self.tun_ip}")

            # Enable IP forwarding (Windows)
            if sys.platform == 'win32':
                os.system('netsh interface ipv4 set interface "{}" forwarding=enabled'.format(tun.name))
                # Set up NAT
                os.system(f'netsh routing ip nat install')
                os.system(f'netsh routing ip nat add interface "{tun.name}" private')

            return tun

        except Exception as e:
            logger.error(f"Failed to create TUN interface: {e}")
            logger.info("Running in proxy mode without TUN")
            return None

    def start(self):
        """Start the tunnel server."""
        logger.info(f"Starting VPN Tunnel Server on {self.host}:{self.port}")

        # Create TUN interface
        self.tun = self.setup_tun_interface()

        # Create server socket
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.server_socket.setblocking(False)

        logger.info(f"Server listening on {self.host}:{self.port}")
        logger.info(f"Encryption: ChaCha20-Poly1305")

        self.running = True
        self.run_event_loop()

    def run_event_loop(self):
        """Main event loop using select."""
        read_list = [self.server_socket]
        if self.tun:
            read_list.append(self.tun)

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
                    elif self.tun and sock is self.tun:
                        self.handle_tun_read()
                    else:
                        self.handle_client_data(sock)

            except KeyboardInterrupt:
                logger.info("Shutting down...")
                break
            except Exception as e:
                logger.error(f"Error in event loop: {e}", exc_info=True)

        self.cleanup()

    def accept_client(self):
        """Accept new client connection."""
        try:
            client_sock, addr = self.server_socket.accept()
            client_sock.setblocking(False)

            logger.info(f"New connection from {addr}")

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
            logger.info(f"HELLO from client: {msg.data.decode('utf-8', errors='ignore')}")
            self.clients[client_sock]['authenticated'] = True

        elif msg.msg_type == MessageType.DATA:
            # IP packet from client - send to internet
            if self.tun:
                try:
                    self.tun.write(msg.data)
                except Exception as e:
                    logger.error(f"Error writing to TUN: {e}")
            else:
                # Proxy mode - parse and forward
                self.forward_packet(msg.data, client_sock)

        elif msg.msg_type == MessageType.KEEPALIVE:
            # Respond with keepalive
            response = create_keepalive_message()
            self.send_to_client(client_sock, response)

        elif msg.msg_type == MessageType.DISCONNECT:
            logger.info(f"Client {self.clients[client_sock]['address']} requested disconnect")
            self.remove_client(client_sock)

    def handle_tun_read(self):
        """Handle packet from TUN interface (response from internet)."""
        try:
            packet = self.tun.read(self.tun.mtu)

            # Send to all authenticated clients
            msg = create_data_message(packet)
            for client_sock, info in list(self.clients.items()):
                if info.get('authenticated'):
                    self.send_to_client(client_sock, msg)

        except Exception as e:
            logger.error(f"Error reading from TUN: {e}")

    def forward_packet(self, ip_packet: bytes, client_sock: socket.socket):
        """Forward packet in proxy mode (without TUN)."""
        # Parse IP packet and forward via raw socket or HTTP proxy
        # This is a simplified version
        try:
            # Extract destination IP and data
            if len(ip_packet) < 20:
                return

            # IP header parsing
            version_ihl = ip_packet[0]
            version = version_ihl >> 4
            ihl = (version_ihl & 0xF) * 4

            if version != 4:
                return

            protocol = ip_packet[9]
            dest_ip = socket.inet_ntoa(ip_packet[16:20])

            logger.debug(f"Forwarding packet to {dest_ip}, protocol {protocol}")

            # For now, just log - full implementation requires raw sockets
            # and complex packet handling

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
            logger.info(f"Removing client {addr}")
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

        if self.tun:
            self.tun.down()
            self.tun.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='VPN Tunnel Server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8888, help='Port to listen on')
    parser.add_argument('--key', required=True, help='Encryption key (hex string)')
    parser.add_argument('--tun-ip', default='10.8.0.1', help='TUN interface IP')

    args = parser.parse_args()

    server = TunnelServer(args.host, args.port, args.key, args.tun_ip)
    server.start()


if __name__ == '__main__':
    main()

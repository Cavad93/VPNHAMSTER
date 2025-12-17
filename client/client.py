"""
VPN Tunnel Client for Mac.
Creates TUN interface and tunnels all traffic through TCP connection to server.
"""

import os
import sys
import socket
import select
import struct
import logging
import argparse
import time
import subprocess
from typing import Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.crypto import TunnelCrypto
from common.protocol import (
    ProtocolMessage, MessageType,
    create_hello_message, create_data_message,
    create_keepalive_message, create_disconnect_message
)

try:
    import pytun
    HAS_PYTUN = True
except ImportError:
    try:
        # Try pytun-pmd3 (Mac support)
        import pytun_pmd3 as pytun
        HAS_PYTUN = True
    except ImportError:
        HAS_PYTUN = False
        print("Warning: pytun not available. Install with: pip install pytun-pmd3")


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TunnelClient:
    """VPN Tunnel Client."""

    def __init__(self, server_host: str, server_port: int, encryption_key: str,
                 tun_ip: str = "10.8.0.2", gateway_ip: str = "10.8.0.1"):
        """
        Initialize tunnel client.

        Args:
            server_host: Server IP address
            server_port: Server TCP port
            encryption_key: Hex string of encryption key
            tun_ip: IP address for local TUN interface
            gateway_ip: Gateway IP (server's TUN IP)
        """
        self.server_host = server_host
        self.server_port = server_port
        self.crypto = TunnelCrypto.from_hex_key(encryption_key)
        self.tun_ip = tun_ip
        self.gateway_ip = gateway_ip

        self.server_socket: Optional[socket.socket] = None
        self.tun = None
        self.running = False
        self.recv_buffer = b''
        self.connected = False

        self.original_gateway = None
        self.tun_name = None

    def setup_tun_interface(self):
        """Create and configure TUN interface."""
        if not HAS_PYTUN:
            logger.error("pytun is required for TUN interface")
            logger.error("Install with: sudo -H pip3 install -r requirements.txt")
            logger.error("Or directly: sudo -H pip3 install pytun-pmd3")
            sys.exit(1)

        try:
            # Create TUN device
            # pytun_pmd3 has different API than python-pytun
            if hasattr(pytun, 'IFF_TUN'):
                # Standard pytun (Linux)
                tun = pytun.TunTapDevice(flags=pytun.IFF_TUN | pytun.IFF_NO_PI)
                tun.addr = self.tun_ip
                tun.netmask = '255.255.255.0'
                tun.dstaddr = self.gateway_ip
                tun.mtu = 1500
                tun.up()
            else:
                # pytun_pmd3 (macOS)
                # Create device first
                tun = pytun.TunTapDevice()
                self.tun_name = tun.name

                # Configure using ifconfig (pytun_pmd3 doesn't support direct addr setting)
                logger.info(f"Configuring {tun.name} with ifconfig...")
                subprocess.run(
                    ['ifconfig', tun.name, self.tun_ip, self.gateway_ip],
                    check=True,
                    capture_output=True
                )

                # Set MTU
                subprocess.run(
                    ['ifconfig', tun.name, 'mtu', '1500'],
                    check=True,
                    capture_output=True
                )

                # Bring up
                tun.up()

            self.tun_name = tun.name

            logger.info(f"TUN interface created: {tun.name}")
            logger.info(f"TUN IP: {self.tun_ip}")
            logger.info(f"Gateway: {self.gateway_ip}")

            return tun

        except PermissionError:
            logger.error("Permission denied creating TUN interface")
            logger.error("Run with sudo: sudo python3 client/client.py ...")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Failed to create TUN interface: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

    def setup_routing(self):
        """Configure routing to send all traffic through tunnel."""
        try:
            logger.info("Setting up routing...")

            # Get current default gateway
            result = subprocess.run(
                ['route', '-n', 'get', 'default'],
                capture_output=True,
                text=True
            )
            for line in result.stdout.split('\n'):
                if 'gateway:' in line:
                    self.original_gateway = line.split(':')[1].strip()
                    break

            if not self.original_gateway:
                logger.warning("Could not determine original gateway")
                return

            logger.info(f"Original gateway: {self.original_gateway}")

            # Add route to server via original gateway
            subprocess.run([
                'route', 'add', '-host', self.server_host,
                self.original_gateway
            ], check=False)

            logger.info(f"Added route to server {self.server_host} via {self.original_gateway}")

            # Set new default route through tunnel
            subprocess.run([
                'route', 'add', '-net', '0.0.0.0',
                self.gateway_ip
            ], check=False)

            logger.info(f"Added default route via {self.gateway_ip}")

            # Set DNS (optional)
            # subprocess.run([
            #     'networksetup', '-setdnsservers', 'Wi-Fi', '8.8.8.8', '8.8.4.4'
            # ], check=False)

            logger.info("Routing configured successfully")

        except Exception as e:
            logger.error(f"Error setting up routing: {e}")

    def restore_routing(self):
        """Restore original routing."""
        if not self.original_gateway:
            return

        try:
            logger.info("Restoring original routing...")

            # Remove route to server
            subprocess.run([
                'route', 'delete', '-host', self.server_host
            ], check=False)

            # Remove tunnel default route
            subprocess.run([
                'route', 'delete', '-net', '0.0.0.0'
            ], check=False)

            logger.info("Routing restored")

        except Exception as e:
            logger.error(f"Error restoring routing: {e}")

    def connect_to_server(self):
        """Connect to tunnel server."""
        logger.info(f"Connecting to {self.server_host}:{self.server_port}")

        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.settimeout(10)
            self.server_socket.connect((self.server_host, self.server_port))
            self.server_socket.setblocking(False)

            logger.info("Connected to server")

            # Send HELLO
            hello_msg = create_hello_message("1.0")
            self.send_to_server(hello_msg)

            # Wait for HELLO_ACK
            time.sleep(0.5)

            self.connected = True
            logger.info("Handshake completed")

            return True

        except socket.timeout:
            logger.error("Connection timeout")
            return False
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False

    def start(self):
        """Start the tunnel client."""
        logger.info("Starting VPN Tunnel Client")

        # Create TUN interface
        self.tun = self.setup_tun_interface()

        # Connect to server
        if not self.connect_to_server():
            logger.error("Failed to connect to server")
            self.cleanup()
            return

        # Setup routing
        self.setup_routing()

        logger.info("Tunnel is UP - all traffic is now routed through the tunnel")
        logger.info("Press Ctrl+C to disconnect")

        self.running = True
        self.run_event_loop()

    def run_event_loop(self):
        """Main event loop."""
        last_keepalive = time.time()
        keepalive_interval = 30  # seconds

        while self.running:
            try:
                read_list = []
                if self.tun:
                    read_list.append(self.tun)
                if self.server_socket:
                    read_list.append(self.server_socket)

                readable, _, exceptional = select.select(
                    read_list,
                    [],
                    [self.server_socket] if self.server_socket else [],
                    1.0
                )

                if self.server_socket in exceptional:
                    logger.error("Server socket error")
                    break

                for sock in readable:
                    if sock is self.tun:
                        self.handle_tun_read()
                    elif sock is self.server_socket:
                        self.handle_server_data()

                # Send keepalive
                if time.time() - last_keepalive > keepalive_interval:
                    self.send_to_server(create_keepalive_message())
                    last_keepalive = time.time()

            except KeyboardInterrupt:
                logger.info("Disconnecting...")
                break
            except Exception as e:
                logger.error(f"Error in event loop: {e}", exc_info=True)
                break

        self.cleanup()

    def handle_tun_read(self):
        """Handle packet from TUN interface (outgoing traffic)."""
        try:
            packet = self.tun.read(self.tun.mtu)

            # Send to server
            msg = create_data_message(packet)
            self.send_to_server(msg)

        except Exception as e:
            if e.errno != 11:  # Ignore EAGAIN
                logger.error(f"Error reading from TUN: {e}")

    def handle_server_data(self):
        """Handle data from server."""
        try:
            data = self.server_socket.recv(8192)
            if not data:
                logger.warning("Server closed connection")
                self.running = False
                return

            self.recv_buffer += data

            # Process messages
            while True:
                if len(self.recv_buffer) < 4:
                    break

                msg_len = struct.unpack('!I', self.recv_buffer[:4])[0]
                if len(self.recv_buffer) < 4 + msg_len:
                    break

                encrypted_msg = self.recv_buffer[4:4+msg_len]
                self.recv_buffer = self.recv_buffer[4+msg_len:]

                try:
                    # Decrypt
                    decrypted = self.crypto.decrypt(encrypted_msg)
                    msg, _ = ProtocolMessage.parse_buffer(decrypted)

                    if msg:
                        self.process_message(msg)

                except Exception as e:
                    logger.error(f"Error processing message: {e}")

        except socket.error as e:
            if e.errno not in (11, 35):  # EAGAIN, EWOULDBLOCK
                logger.error(f"Socket error: {e}")
                self.running = False
        except Exception as e:
            logger.error(f"Error handling server data: {e}")

    def process_message(self, msg: ProtocolMessage):
        """Process a protocol message."""
        if msg.msg_type == MessageType.HELLO_ACK:
            logger.debug("Received HELLO_ACK")

        elif msg.msg_type == MessageType.DATA:
            # IP packet from server - write to TUN
            try:
                self.tun.write(msg.data)
            except Exception as e:
                logger.error(f"Error writing to TUN: {e}")

        elif msg.msg_type == MessageType.KEEPALIVE:
            logger.debug("Received KEEPALIVE")

        elif msg.msg_type == MessageType.DISCONNECT:
            logger.info("Server requested disconnect")
            self.running = False

    def send_to_server(self, msg: ProtocolMessage):
        """Send message to server."""
        try:
            encrypted = self.crypto.encrypt(msg.serialize())
            framed = struct.pack('!I', len(encrypted)) + encrypted
            self.server_socket.sendall(framed)
        except Exception as e:
            logger.error(f"Error sending to server: {e}")
            self.running = False

    def cleanup(self):
        """Clean up resources."""
        logger.info("Cleaning up...")

        # Send disconnect message
        if self.server_socket and self.connected:
            try:
                self.send_to_server(create_disconnect_message())
                time.sleep(0.5)
            except:
                pass

        # Restore routing
        self.restore_routing()

        # Close server socket
        if self.server_socket:
            self.server_socket.close()

        # Close TUN
        if self.tun:
            self.tun.down()
            self.tun.close()

        logger.info("Tunnel closed")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='VPN Tunnel Client')
    parser.add_argument('--server', required=True, help='Server IP address')
    parser.add_argument('--port', type=int, default=8888, help='Server port')
    parser.add_argument('--key', required=True, help='Encryption key (hex string)')
    parser.add_argument('--tun-ip', default='10.8.0.2', help='TUN interface IP')
    parser.add_argument('--gateway', default='10.8.0.1', help='Gateway IP')

    args = parser.parse_args()

    # Check if running as root
    if os.geteuid() != 0:
        logger.error("This script must be run as root (use sudo)")
        sys.exit(1)

    client = TunnelClient(
        args.server,
        args.port,
        args.key,
        args.tun_ip,
        args.gateway
    )
    client.start()


if __name__ == '__main__':
    main()

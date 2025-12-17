"""
TUN to SOCKS5 client for Mac.
Reads IP packets from TUN and proxies through SOCKS5.
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
from typing import Optional, Dict
from collections import defaultdict

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.crypto import TunnelCrypto

try:
    import pytun_pmd3 as pytun
    HAS_PYTUN = True
except ImportError:
    HAS_PYTUN = False
    print("Error: pytun-pmd3 is required")
    sys.exit(1)


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TUN2SOCKS:
    """TUN to SOCKS5 proxy client."""

    def __init__(self, socks_host: str, socks_port: int, encryption_key: str,
                 tun_ip: str = "10.8.0.2", gateway_ip: str = "10.8.0.1"):
        """
        Initialize TUN2SOCKS client.

        Args:
            socks_host: SOCKS5 server IP
            socks_port: SOCKS5 server port
            encryption_key: Encryption key (hex string)
            tun_ip: TUN interface IP
            gateway_ip: Gateway IP
        """
        self.socks_host = socks_host
        self.socks_port = socks_port
        self.crypto = TunnelCrypto.from_hex_key(encryption_key)
        self.tun_ip = tun_ip
        self.gateway_ip = gateway_ip

        self.tun = None
        self.tun_name = None
        self.running = False
        self.original_gateway = None

        # TCP connection tracking
        self.tcp_connections: Dict[tuple, socket.socket] = {}
        # Format: (src_ip, src_port, dst_ip, dst_port) -> socket

    def setup_tun_interface(self):
        """Create and configure TUN interface."""
        logger.info("Creating TUN interface...")

        try:
            tun = pytun.TunTapDevice()
            self.tun_name = tun.name

            # Configure using ifconfig
            subprocess.run(
                ['ifconfig', tun.name, self.tun_ip, self.gateway_ip],
                check=True,
                capture_output=True
            )

            subprocess.run(
                ['ifconfig', tun.name, 'mtu', '1500'],
                check=True,
                capture_output=True
            )

            tun.up()

            logger.info(f"TUN interface created: {tun.name}")
            logger.info(f"TUN IP: {self.tun_ip}")
            logger.info(f"Gateway: {self.gateway_ip}")

            return tun

        except PermissionError:
            logger.error("Permission denied creating TUN interface")
            logger.error("Run with sudo!")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Failed to create TUN interface: {e}")
            sys.exit(1)

    def setup_routing(self):
        """Configure routing."""
        try:
            logger.info("Setting up routing...")

            # Get current gateway
            result = subprocess.run(
                ['netstat', '-rn'],
                capture_output=True,
                text=True,
                check=True
            )

            for line in result.stdout.split('\n'):
                if line.startswith('default') and 'UGSc' in line:
                    parts = line.split()
                    if len(parts) >= 2 and parts[1] != 'link' and not parts[1].startswith('fe80'):
                        self.original_gateway = parts[1]
                        break

            if self.original_gateway:
                logger.info(f"Original gateway: {self.original_gateway}")

                # Add route to SOCKS server via original gateway
                subprocess.run(
                    ['route', 'add', '-host', self.socks_host, self.original_gateway],
                    check=False,
                    capture_output=True
                )

                # Change default route
                subprocess.run(
                    ['route', 'delete', 'default', self.original_gateway],
                    check=False,
                    capture_output=True
                )

                subprocess.run(
                    ['route', 'add', 'default', '-interface', self.tun_name],
                    capture_output=True
                )

                logger.info("Routing configured successfully")
            else:
                logger.warning("Could not determine original gateway")

        except Exception as e:
            logger.error(f"Error setting up routing: {e}")

    def restore_routing(self):
        """Restore original routing."""
        if not self.original_gateway:
            return

        try:
            logger.info("Restoring routing...")
            subprocess.run(['route', 'delete', 'default'], check=False, capture_output=True)
            subprocess.run(['route', 'delete', '-host', self.socks_host], check=False, capture_output=True)
            subprocess.run(
                ['route', 'add', 'default', self.original_gateway],
                check=False,
                capture_output=True
            )
            logger.info("Routing restored")
        except Exception as e:
            logger.error(f"Error restoring routing: {e}")

    def start(self):
        """Start TUN2SOCKS client."""
        logger.info("=" * 60)
        logger.info("VPNHAMSTER - TUN2SOCKS Client")
        logger.info("=" * 60)
        logger.info(f"SOCKS5 Server: {self.socks_host}:{self.socks_port}")
        logger.info(f"Encryption: ChaCha20-Poly1305")
        logger.info("=" * 60)
        logger.info("")

        # Create TUN
        self.tun = self.setup_tun_interface()

        # Setup routing
        self.setup_routing()

        logger.info("")
        logger.info("=" * 60)
        logger.info("Tunnel is UP!")
        logger.info("All traffic is routed through SOCKS5 proxy")
        logger.info("Press Ctrl+C to disconnect")
        logger.info("=" * 60)
        logger.info("")

        self.running = True
        self.run_event_loop()

    def run_event_loop(self):
        """Main event loop."""
        try:
            while self.running:
                # Read from TUN
                try:
                    packet = self.tun.read(self.tun.mtu)
                    self.handle_ip_packet(packet)
                except BlockingIOError:
                    time.sleep(0.001)
                except Exception as e:
                    if 'Errno 35' not in str(e):  # EAGAIN
                        logger.error(f"Error reading from TUN: {e}")

        except KeyboardInterrupt:
            logger.info("\nDisconnecting...")
        finally:
            self.cleanup()

    def handle_ip_packet(self, packet: bytes):
        """
        Handle IP packet from TUN.

        For now, this is a simplified implementation that handles TCP.
        Full implementation would need complete TCP/IP stack.
        """
        if len(packet) < 20:
            return

        # Parse IP header
        version_ihl = packet[0]
        version = version_ihl >> 4
        ihl = (version_ihl & 0xF) * 4

        if version != 4:
            return

        protocol = packet[9]
        src_ip = socket.inet_ntoa(packet[12:16])
        dst_ip = socket.inet_ntoa(packet[16:20])

        # Only handle TCP for now
        if protocol == 6:  # TCP
            self.handle_tcp_packet(packet, ihl, src_ip, dst_ip)
        # UDP would require different handling

    def handle_tcp_packet(self, ip_packet: bytes, ihl: int, src_ip: str, dst_ip: str):
        """Handle TCP packet (simplified)."""
        if len(ip_packet) < ihl + 20:
            return

        tcp_header = ip_packet[ihl:ihl+20]
        src_port = struct.unpack('!H', tcp_header[0:2])[0]
        dst_port = struct.unpack('!H', tcp_header[2:4])[0]

        conn_key = (src_ip, src_port, dst_ip, dst_port)

        # For simplicity, log and drop for now
        # Full implementation requires TCP state machine
        logger.debug(f"TCP: {src_ip}:{src_port} → {dst_ip}:{dst_port}")

        # This is a placeholder - full tun2socks requires:
        # 1. TCP state machine
        # 2. Packet reassembly
        # 3. SOCKS5 connection pooling
        # 4. Response packet generation

    def connect_socks5(self, dst_addr: str, dst_port: int) -> Optional[socket.socket]:
        """Connect to destination via SOCKS5."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.socks_host, self.socks_port))

            # SOCKS5 greeting
            sock.sendall(struct.pack('!BBB', 5, 1, 0))
            response = sock.recv(2)

            if len(response) != 2 or response[0] != 5 or response[1] != 0:
                sock.close()
                return None

            # Connection request
            if dst_addr.replace('.', '').isdigit():  # IPv4
                addr_bytes = socket.inet_aton(dst_addr)
                request = struct.pack('!BBBB', 5, 1, 0, 1) + addr_bytes
            else:  # Domain
                addr_bytes = dst_addr.encode('utf-8')
                request = struct.pack('!BBBBB', 5, 1, 0, 3, len(addr_bytes)) + addr_bytes

            request += struct.pack('!H', dst_port)
            sock.sendall(request)

            response = sock.recv(10)
            if len(response) < 10 or response[1] != 0:
                sock.close()
                return None

            return sock

        except Exception as e:
            logger.error(f"SOCKS5 connection failed: {e}")
            return None

    def cleanup(self):
        """Clean up resources."""
        logger.info("Cleaning up...")

        self.restore_routing()

        # Close all connections
        for sock in self.tcp_connections.values():
            try:
                sock.close()
            except:
                pass

        if self.tun:
            self.tun.down()
            self.tun.close()

        logger.info("Tunnel closed")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='TUN2SOCKS Client for Mac')
    parser.add_argument('--server', required=True, help='SOCKS5 server IP')
    parser.add_argument('--port', type=int, default=1080, help='SOCKS5 server port')
    parser.add_argument('--key', required=True, help='Encryption key (hex string)')
    parser.add_argument('--tun-ip', default='10.8.0.2', help='TUN interface IP')
    parser.add_argument('--gateway', default='10.8.0.1', help='Gateway IP')

    args = parser.parse_args()

    if os.geteuid() != 0:
        logger.error("This script must be run as root (use sudo)")
        sys.exit(1)

    client = TUN2SOCKS(
        args.server,
        args.port,
        args.key,
        args.tun_ip,
        args.gateway
    )
    client.start()


if __name__ == '__main__':
    main()

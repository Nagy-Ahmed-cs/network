#!/usr/bin/env python3
import socket
import time
import random
import threading
import argparse
import sys

# Import your custom protocol constants and functions
from protocol import build_packet, DATA, HEARTBEAT

class SensorClient:
    def __init__(self, device_id, reporting_interval=1, heartbeat_interval=5,
                 batch_size=1, server_ip="127.0.0.1", server_port=5555):
        
        # Device configuration (Device ID must fit in uint16)
        self.device_id = int(device_id) & 0xFFFF
        self.reporting_interval = float(reporting_interval)
        self.heartbeat_interval = float(heartbeat_interval)
        self.batch_size = max(1, int(batch_size))

        # Server settings
        self.server = (server_ip, server_port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Sequence number (4-byte unsigned int)
        self.seq = 0
        self.running = True

        # Start heartbeat thread (Requirement: periodically send when no data available)
        self.hb_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.hb_thread.start()

    def _make_reading(self):
        """Generate a mock sensor reading (temperature)."""
        return round(random.uniform(20.0, 30.0), 2)

    def send_data(self):
        """Builds and sends a DATA packet containing a batch of readings."""
        readings = [self._make_reading() for _ in range(self.batch_size)]
        
        # Build binary packet using protocol.py
        pkt = build_packet(self.device_id, self.seq, DATA, readings)
        
        try:
            self.sock.sendto(pkt, self.server)
            print(f"[Client {self.device_id}] sent DATA seq={self.seq} batch={len(readings)}", flush=True)
            
            # Increment sequence number for DATA packets
            self.seq = (self.seq + 1) & 0xFFFFFFFF
        except Exception as e:
            print(f"[Client {self.device_id}] Send Error: {e}", flush=True)

    def send_heartbeat(self):
        """Sends a HEARTBEAT packet (no data payload)."""
        # Note: We send the current seq without incrementing it
        pkt = build_packet(self.device_id, self.seq, HEARTBEAT, [])
        try:
            self.sock.sendto(pkt, self.server)
            print(f"[Client {self.device_id}] sent HEARTBEAT seq={self.seq}", flush=True)
        except Exception as e:
            print(f"[Client {self.device_id}] HB Error: {e}", flush=True)

    def _heartbeat_loop(self):
        """Background loop to send heartbeats."""
        while self.running:
            time.sleep(self.heartbeat_interval)
            if self.running:
                self.send_heartbeat()

    def run(self, duration=None):
        """Main loop that sends data periodically for a set duration."""
        print(f"[Client {self.device_id}] Reporting every {self.reporting_interval}s, Batching={self.batch_size}", flush=True)
        start_time = time.time()

        try:
            while self.running:
                # Check if test duration is reached
                if duration and (time.time() - start_time >= duration):
                    print(f"[Client {self.device_id}] Duration reached. Stopping...", flush=True)
                    break

                self.send_data()
                time.sleep(self.reporting_interval)

        except KeyboardInterrupt:
            print(f"[Client {self.device_id}] Interrupted by user.", flush=True)
        finally:
            self.running = False
            self.sock.close()

if __name__ == "__main__":
    # Parsing command line arguments for the shell script (run_experiments.sh)
    parser = argparse.ArgumentParser(description="IoT Telemetry Sensor Client")
    parser.add_argument("--id", type=int, default=101, help="Device ID")
    parser.add_argument("--interval", type=float, default=1.0, help="Reporting interval in seconds")
    parser.add_argument("--batch", type=int, default=1, help="Number of readings per packet")
    parser.add_argument("--duration", type=int, default=60, help="Duration to run the client in seconds")
    parser.add_argument("--ip", type=str, default="127.0.0.1", help="Server IP address")
    
    args = parser.parse_args()

    # Create and run the client
    client = SensorClient(
        device_id=args.id,
        reporting_interval=args.interval,
        batch_size=args.batch,
        server_ip=args.ip
    )
    
    client.run(duration=args.duration)

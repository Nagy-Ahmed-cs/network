# client.py
import socket
import time
import random
import threading

from protocol import build_packet, DATA, HEARTBEAT

class SensorClient:
    def __init__(self, device_id, reporting_interval=1, heartbeat_interval=5,
                 batch_size=1, server_ip="127.0.0.1", server_port=5555):
        # Device configuration
        self.device_id = int(device_id) & 0xFFFF
        self.reporting_interval = reporting_interval
        self.heartbeat_interval = heartbeat_interval
        self.batch_size = max(1, batch_size)

        # Server settings
        self.server = (server_ip, server_port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Sequence number (only for DATA messages)
        self.seq = 0

        # Running flag
        self.running = True

        # Simple FSM
        self.state = "WAIT_FOR_DATA"

        # Start heartbeat thread
        threading.Thread(target=self._heartbeat_loop, daemon=True).start()

    # ---------------------------
    # Internal helpers
    # ---------------------------

    def _make_reading(self):
        """Generate a mock sensor reading (temperature example)."""
        return round(random.uniform(20.0, 30.0), 2)

    # ---------------------------
    # Packet senders
    # ---------------------------

    def send_data(self, readings):
        """Send DATA packet with the current seq number."""
        pkt = build_packet(self.device_id, self.seq, DATA, readings)
        try:
            self.sock.sendto(pkt, self.server)
        except Exception as e:
            print("send error:", e)

        print(f"[Client {self.device_id}] sent DATA seq={self.seq} readings={len(readings)}")

        # Increment sequence only for DATA packets
        self.seq = (self.seq + 1) & 0xFFFFFFFF

    def send_heartbeat(self):
        """
        Send HEARTBEAT without incrementing seq.
        This avoids artificial sequence gaps and is Phase-2 compliant.
        """
        pkt = build_packet(self.device_id, self.seq, HEARTBEAT, [])

        try:
            self.sock.sendto(pkt, self.server)
        except Exception as e:
            print("hb send error:", e)

        print(f"[Client {self.device_id}] sent HEARTBEAT seq={self.seq}")
        # NO seq increment here (intentional)

    # ---------------------------
    # Background heartbeat loop
    # ---------------------------

    def _heartbeat_loop(self):
        while self.running:
            time.sleep(self.heartbeat_interval)
            self.send_heartbeat()

    # ---------------------------
    # Main client loop
    # ---------------------------

    def run(self, duration=None):
        """Main loop that repeatedly sends DATA packets."""
        start = time.time()

        try:
            while self.running:
                # Stop after given duration
                if duration and (time.time() - start >= duration):
                    break

                if self.state == "WAIT_FOR_DATA":
                    readings = [self._make_reading() for _ in range(self.batch_size)]
                    self.state = "SEND_DATA"

                if self.state == "SEND_DATA":
                    self.send_data(readings)
                    self.state = "WAIT_FOR_DATA"
                    time.sleep(self.reporting_interval)

        except KeyboardInterrupt:
            pass

        finally:
            self.running = False

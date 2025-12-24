# Client.py
import socket
import time
import random
from Protocol import build_packet, DATA, HEARTBEAT

class SensorClient:
    def __init__(self, device_id, reporting_interval=1, server_ip="127.0.0.1", server_port=5555):
        self.device_id = device_id
        self.reporting_interval = reporting_interval
        self.server = (server_ip, server_port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.seq = 0

    def send_data(self, readings):
        packet = build_packet(self.device_id, self.seq, DATA, readings)
        self.sock.sendto(packet, self.server)
        print(f"[Client {self.device_id}] Sent seq={self.seq} DATA {readings}")
        self.seq += 1

    def send_heartbeat(self):
        packet = build_packet(self.device_id, self.seq, HEARTBEAT, [])
        self.sock.sendto(packet, self.server)
        print(f"[Client {self.device_id}] Sent seq={self.seq} HEARTBEAT")
        self.seq += 1

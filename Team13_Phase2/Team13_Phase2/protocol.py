# protocol.py
# TinyTelemetry v1 — compact 12-byte header
# Header (network byte order / big-endian):
# device_id (uint16) | seq (uint32) | timestamp (uint32) | msg_type (uint8) | batch_count (uint8)
# sizes: 2 + 4 + 4 + 1 + 1 = 12 bytes

import struct
import time

PROTOCOL_NAME = "TinyTelemetry"
VERSION = 1

DATA = 1
HEARTBEAT = 2

HEADER_FORMAT = "!H I I B B"   # device_id, seq, timestamp, msg_type, batch_count
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
READING_SIZE = 4  # float32 per reading

def now_ts():
    return int(time.time())

def build_packet(device_id: int, seq: int, msg_type: int, readings: list):
    """
    Build a packet with 12-byte header and payload of float32 readings.
    readings: list of floats
    """
    timestamp = now_ts()
    batch_count = len(readings)
    header = struct.pack(HEADER_FORMAT, device_id & 0xFFFF, seq & 0xFFFFFFFF, timestamp & 0xFFFFFFFF, msg_type & 0xFF, batch_count & 0xFF)
    body = b"".join(struct.pack("!f", float(r)) for r in readings)
    return header + body

def parse_header(data: bytes):
    if len(data) < HEADER_SIZE:
        raise ValueError("packet too short for header")
    device_id, seq, timestamp, msg_type, batch_count = struct.unpack(HEADER_FORMAT, data[:HEADER_SIZE])
    return device_id, seq, timestamp, msg_type, batch_count

def parse_readings(data: bytes, count: int):
    readings = []
    for i in range(count):
        start = i * READING_SIZE
        chunk = data[start:start + READING_SIZE]
        if len(chunk) < READING_SIZE:
            raise ValueError("not enough bytes for reading")
        readings.append(struct.unpack("!f", chunk)[0])
    return readings

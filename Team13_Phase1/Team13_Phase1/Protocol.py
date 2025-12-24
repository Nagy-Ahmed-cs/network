# Protocol.py
import struct
import time

# ===== Protocol Constants =====
PROTOCOL_NAME = "LiteTelemetry"
VERSION = 1

# Message Types
DATA = 1
HEARTBEAT = 2

# Header Format:
# device_id (H), seq (I), timestamp (I), msg_type (B), batch_count (B)
HEADER_FORMAT = "!H I I B B"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
READING_SIZE = 4  # float32 (IEEE 754)

# ===== Build & Parse =====
def build_packet(device_id, seq, msg_type, readings):
    timestamp = int(time.time())
    header = struct.pack(HEADER_FORMAT, device_id, seq, timestamp, msg_type, len(readings))
    body = b''.join(struct.pack("!f", r) for r in readings)
    return header + body

def parse_header(data):
    return struct.unpack(HEADER_FORMAT, data[:HEADER_SIZE])

def parse_readings(data, count):
    return [struct.unpack("!f", data[i*4:(i+1)*4])[0] for i in range(count)]

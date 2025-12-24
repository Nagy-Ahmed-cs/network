# Server.py
import socket
import struct
import time
import csv
import threading
import collections
import signal
import sys
import json
from Protocol import HEADER_SIZE, parse_header, parse_readings, DATA, HEARTBEAT

SERVER_IP = "0.0.0.0"
SERVER_PORT = 5555

LOG_CSV = "telemetry_log.csv"
REORDERED_CSV = "telemetry_reordered.csv"
METRICS_JSON = "metrics.json"

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind((SERVER_IP, SERVER_PORT))
print(f"[Server] Listening on {SERVER_IP}:{SERVER_PORT}")

device_states = {}
metrics = {
    "packets_received": 0,
    "bytes_received": 0,
    "duplicates": 0,
    "gaps": 0,
    "reads_processed": 0,
    "processing_cpu_seconds": 0.0
}

device_lock = threading.Lock()
metrics_lock = threading.Lock()
reorder_lock = threading.Lock()
reorder_buffer = []

log_file = open(LOG_CSV, "w", newline="")
log_writer = csv.writer(log_file)
log_writer.writerow(["device_id", "seq", "timestamp", "arrival_time", "duplicate_flag", "gap_flag"])

reordered_file = open(REORDERED_CSV, "w", newline="")
reordered_writer = csv.writer(reordered_file)
reordered_writer.writerow(["device_id", "seq", "timestamp", "arrival_time", "readings_count", "readings"])

start_cpu = time.process_time()

def flush_reorder_buffer():
    with reorder_lock:
        reorder_buffer.sort(key=lambda x: x[0])
        for pkt_ts, device_id, seq, readings, arrival in reorder_buffer:
            reordered_writer.writerow([device_id, seq, pkt_ts, arrival, len(readings), ";".join(map(str, readings))])
        reordered_file.flush()
        reorder_buffer.clear()

def signal_handler(sig, frame):
    print("[Server] Shutting down gracefully...")
    metrics["processing_cpu_seconds"] = time.process_time() - start_cpu
    with open(METRICS_JSON, "w") as mf:
        json.dump(metrics, mf, indent=2)
    flush_reorder_buffer()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def process_packet(data, addr):
    arrival_time = int(time.time())
    with metrics_lock:
        metrics["packets_received"] += 1
        metrics["bytes_received"] += len(data)

    if len(data) < HEADER_SIZE:
        return

    device_id, seq, pkt_ts, msg_type, batch = parse_header(data)
    payload = data[HEADER_SIZE:]
    readings = parse_readings(payload, batch) if msg_type == DATA else []

    duplicate = 0
    gap = 0
    with device_lock:
        st = device_states.get(device_id)
        if st is None:
            device_states[device_id] = {"last_seq": seq, "recent": set()}
        else:
            if seq in st["recent"]:
                duplicate = 1
                metrics["duplicates"] += 1
            elif seq > st["last_seq"] + 1:
                gap = 1
                metrics["gaps"] += 1
            st["recent"].add(seq)
            st["last_seq"] = seq

    log_writer.writerow([device_id, seq, pkt_ts, arrival_time, duplicate, gap])
    log_file.flush()

    with reorder_lock:
        reorder_buffer.append((pkt_ts, device_id, seq, readings, arrival_time))

    with metrics_lock:
        metrics["reads_processed"] += max(1, len(readings))

    print(f"[Server] Device={device_id} Seq={seq} Type={'DATA' if msg_type==DATA else 'HEARTBEAT'} dup={duplicate} gap={gap}")

def server_loop():
    while True:
        data, addr = sock.recvfrom(4096)
        threading.Thread(target=process_packet, args=(data, addr), daemon=True).start()

if __name__ == "__main__":
    print("[Server] Ready. Press Ctrl+C to stop.")
    server_loop()

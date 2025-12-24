# server.py
import socket
import time
import csv
import threading
import collections
import signal
import sys
import json
import os

from protocol import HEADER_SIZE, parse_header, parse_readings, DATA, HEARTBEAT

# config
SERVER_IP = "0.0.0.0"
SERVER_PORT = 5555
HEARTBEAT_TIMEOUT = 10       # seconds to declare device offline
REORDER_FLUSH_INTERVAL = 5   # seconds
METRICS_DUMP_INTERVAL = 2    # seconds
RECENT_WINDOW = 500          # number of recent seqs to remember per device

# outputs
LOG_CSV = "telemetry_log.csv"
REORDERED_CSV = "telemetry_reordered.csv"
METRICS_JSON = "metrics.json"

# socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind((SERVER_IP, SERVER_PORT))
print(f"[Server] Listening on {SERVER_IP}:{SERVER_PORT}")

# per-device state and global metrics
device_states = {}  # device_id -> { last_seq, recent(deque), last_heartbeat, offline_flag }
device_lock = threading.Lock()

metrics = {
    "packets_received": 0,
    "bytes_received": 0,
    "duplicates": 0,
    "gaps": 0,
    "reads_processed": 0,
    "processing_cpu_seconds": 0.0
}
metrics_lock = threading.Lock()

reorder_buffer = []   # list of tuples (pkt_timestamp, device_id, seq, readings, arrival_time)
reorder_lock = threading.Lock()

# ensure output files exist and header rows
log_file = open(LOG_CSV, "w", newline="")
log_writer = csv.writer(log_file)
log_writer.writerow(["device_id", "seq", "timestamp", "arrival_time", "duplicate_flag", "gap_flag", "heartbeat_flag", "offline_flag"])

reordered_file = open(REORDERED_CSV, "w", newline="")
reordered_writer = csv.writer(reordered_file)
reordered_writer.writerow(["device_id", "seq", "timestamp", "arrival_time", "readings_count", "readings"])

start_cpu = time.process_time()
running = True

# helper funcs
def flush_reorder_buffer():
    with reorder_lock:
        reorder_buffer.sort(key=lambda x: x[0])  # sort by packet timestamp
        for pkt_ts, device_id, seq, readings, arrival in reorder_buffer:
            reordered_writer.writerow([device_id, seq, pkt_ts, arrival, len(readings), ";".join(map(str, readings))])
        reordered_file.flush()
        reorder_buffer.clear()

def monitor_offline():
    while running:
        time.sleep(1)
        now = int(time.time())
        with device_lock:
            for dev, st in device_states.items():
                if 'last_heartbeat' in st:
                    st['offline'] = (now - st['last_heartbeat'] > HEARTBEAT_TIMEOUT)
                else:
                    st['offline'] = True

def periodic_flush_and_metrics():
    while running:
        time.sleep(REORDER_FLUSH_INTERVAL)
        flush_reorder_buffer()
        # dump metrics JSON periodically
        with metrics_lock:
            reads = metrics.get("reads_processed", 0)
            packets = metrics.get("packets_received", 0)
            bytes_recv = metrics.get("bytes_received", 0)
            duplicates = metrics.get("duplicates", 0)
            gaps = metrics.get("gaps", 0)
            cpu_s = metrics.get("processing_cpu_seconds", 0.0)
            cpu_ms_per_report = (cpu_s / reads * 1000.0) if reads > 0 else 0.0
            bytes_per_report = (bytes_recv / reads) if reads > 0 else 0.0
            duplicate_rate = (duplicates / packets) if packets > 0 else 0.0
            dump = {
                "packets_received": packets,
                "reads_processed": reads,
                "bytes_received": bytes_recv,
                "bytes_per_report": bytes_per_report,
                "duplicates": duplicates,
                "duplicate_rate": duplicate_rate,
                "gaps": gaps,
                "cpu_ms_per_report": cpu_ms_per_report,
                "timestamp": int(time.time())
            }
        try:
            with open(METRICS_JSON, "w") as mf:
                json.dump(dump, mf, indent=2)
        except Exception as e:
            print("metrics write error:", e)

def shutdown(sig, frame):
    global running
    print("[Server] Shutting down...")
    running = False
    metrics["processing_cpu_seconds"] += time.process_time() - start_cpu
    # final flushes
    flush_reorder_buffer()
    with metrics_lock:
        try:
            with open(METRICS_JSON, "w") as mf:
                json.dump(metrics, mf, indent=2)
        except:
            pass
    try:
        log_file.close()
        reordered_file.close()
    except:
        pass
    sys.exit(0)

signal.signal(signal.SIGINT, shutdown)
signal.signal(signal.SIGTERM, shutdown)

# start background threads
threading.Thread(target=monitor_offline, daemon=True).start()
threading.Thread(target=periodic_flush_and_metrics, daemon=True).start()

def process_packet(data: bytes, addr):
    t0 = time.process_time()
    arrival_time = int(time.time())
    with metrics_lock:
        metrics["packets_received"] += 1
        metrics["bytes_received"] += len(data)

    if len(data) < HEADER_SIZE:
        # ignore malformed
        return

    try:
        device_id, seq, pkt_ts, msg_type, batch = parse_header(data)
    except Exception:
        return
    payload = data[HEADER_SIZE:]
    readings = []
    if msg_type == DATA and batch > 0:
        try:
            readings = parse_readings(payload, batch)
        except Exception:
            # malformed payload: skip reading parse but still log packet
            readings = []

    duplicate = 0
    gap = 0
    heartbeat_flag = 1 if msg_type == HEARTBEAT else 0
    offline_flag = 0

    with device_lock:
        st = device_states.get(device_id)
        if st is None:
            st = {"last_seq": seq, "recent": collections.deque(maxlen=RECENT_WINDOW), "offline": True}
            device_states[device_id] = st

        if msg_type == HEARTBEAT:
            st['last_heartbeat'] = arrival_time
            st['offline'] = False

        if msg_type == DATA:
            # duplicate if seq in recent window
            if seq in st['recent']:
                duplicate = 1
                with metrics_lock:
                    metrics["duplicates"] += 1
            elif seq > st['last_seq'] + 1:
                gap = 1
                with metrics_lock:
                    metrics["gaps"] += 1
            st['recent'].append(seq)
            st['last_seq'] = seq

        offline_flag = 1 if st.get('offline', False) else 0

    # log CSV line
    log_writer.writerow([device_id, seq, pkt_ts, arrival_time, int(duplicate), int(gap), int(heartbeat_flag), int(offline_flag)])
    log_file.flush()

    # add to reorder buffer for DATA only
    if msg_type == DATA:
        with reorder_lock:
            reorder_buffer.append((pkt_ts, device_id, seq, readings, arrival_time))

    with metrics_lock:
        metrics["reads_processed"] += max(1, len(readings))

    t1 = time.process_time()
    with metrics_lock:
        metrics["processing_cpu_seconds"] += (t1 - t0)

    print(f"[Server] dev={device_id} seq={seq} type={'DATA' if msg_type==DATA else 'HB'} dup={duplicate} gap={gap} offline={offline_flag}")

def server_loop():
    while True:
        data, addr = sock.recvfrom(4096)
        threading.Thread(target=process_packet, args=(data, addr), daemon=True).start()

if __name__ == "__main__":
    print("[Server] Ready. Press Ctrl+C to stop.")
    server_loop()

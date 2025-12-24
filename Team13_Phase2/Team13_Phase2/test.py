# test_phase2.py
# Expanded test runner for Phase-2 (uses eth0 for netem)
import subprocess
import os
import time
import sys
import shutil
import random
import json
import signal

PY = sys.executable
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(PROJECT_DIR, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

SERVER_SCRIPT = os.path.join(PROJECT_DIR, "server.py")
SCENARIO_WRAPPER = os.path.join(PROJECT_DIR, "scenario_client_run.py")
NET_IF = "eth0"   # <- confirmed by you

def start_server():
    proc = subprocess.Popen([PY, SERVER_SCRIPT], cwd=PROJECT_DIR)
    time.sleep(1.0)
    return proc

def stop_server(proc):
    if not proc:
        return
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except:
        proc.kill()

def apply_netem(cmd):
    # cmd is the netem parameters e.g., "loss 5%" or "delay 100ms 10ms"
    try:
        subprocess.run(["sudo", "tc", "qdisc", "add", "dev", NET_IF, "root", "netem"] + cmd.split(), check=True)
        print("[netem] applied:", cmd)
    except Exception as e:
        print("[netem] apply error:", e)

def clear_netem():
    try:
        subprocess.run(["sudo", "tc", "qdisc", "del", "dev", NET_IF, "root"], check=True)
        print("[netem] cleared")
    except Exception as e:
        print("[netem] clear error (maybe none applied):", e)

def run_wrapper(duration, reporting_interval, loss_prob, batch, outdir):
    # writes a small wrapper and runs it
    wrapper_body = f"""import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from client import SensorClient
import time, random
DEVICE_ID = {random.randint(1000,9999)}
REPORTING_INTERVAL = {reporting_interval}
DURATION = {duration}
LOSS_PROB = {loss_prob}
BATCH = {batch}
c = SensorClient(device_id=DEVICE_ID, reporting_interval=REPORTING_INTERVAL, batch_size=BATCH)
start = time.time()
while time.time()-start < DURATION:
    if random.random() > LOSS_PROB:
        c.send_data([round(random.uniform(20,30),2) for _ in range(BATCH)])
    else:
        print('[wrapper] simulated loss')
    time.sleep(REPORTING_INTERVAL)
c.running = False
"""
    with open(SCENARIO_WRAPPER, "w") as f:
        f.write(wrapper_body)
    try:
        subprocess.run([PY, SCENARIO_WRAPPER], cwd=PROJECT_DIR, check=True)
    finally:
        try:
            os.remove(SCENARIO_WRAPPER)
        except:
            pass

def collect_outputs(outdir):
    for fname in ["telemetry_log.csv", "telemetry_reordered.csv", "metrics.json"]:
        src = os.path.join(PROJECT_DIR, fname)
        if os.path.exists(src):
            shutil.copy(src, os.path.join(outdir, fname))

def run_scenario(name, duration=20, reporting_interval=1, loss_prob=0.0, batch=1, netem=None):
    print(f"\n=== scenario: {name} ===")
    outdir = os.path.join(RESULTS_DIR, name.replace(" ", "_"))
    if os.path.exists(outdir):
        shutil.rmtree(outdir)
    os.makedirs(outdir, exist_ok=True)

    server_proc = start_server()
    time.sleep(0.5)

    try:
        if netem:
            apply_netem(netem)
            time.sleep(0.2)

        run_wrapper(duration, reporting_interval, loss_prob, batch, outdir)
    finally:
        clear_netem()
        stop_server(server_proc)
        time.sleep(0.5)
        collect_outputs(outdir)
        with open(os.path.join(outdir, "notes.txt"), "w") as nf:
            nf.write(json.dumps({"duration": duration, "reporting_interval": reporting_interval, "loss_prob": loss_prob, "batch": batch}))
        print(f"scenario '{name}' done, results in {outdir}")

if __name__ == "__main__":
    # baseline
    run_scenario("baseline_1s", duration=20, reporting_interval=1, loss_prob=0.0, batch=1)
    # loss 5%
    run_scenario("loss_5pct", duration=20, reporting_interval=1, loss_prob=0.05, batch=1)
    # delay + jitter 100ms +-10ms (netem)
    run_scenario("delay_100ms_10ms", duration=20, reporting_interval=1, loss_prob=0.0, batch=1, netem="delay 100ms 10ms")
    # different intervals
    run_scenario("interval_5s", duration=60, reporting_interval=5, loss_prob=0.0, batch=1)
    run_scenario("interval_30s", duration=120, reporting_interval=30, loss_prob=0.0, batch=1)
    # batching experiments
    run_scenario("batch_5", duration=30, reporting_interval=1, loss_prob=0.0, batch=5)
    run_scenario("batch_10", duration=30, reporting_interval=1, loss_prob=0.0, batch=10)
    print("All scenarios finished.")

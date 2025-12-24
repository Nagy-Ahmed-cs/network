# test.py
import threading
import time
import random
import subprocess
from Client import SensorClient

def run_server():
    subprocess.Popen(["python", "Server.py"])

def simulate_loss(client, loss_prob=0.05):
    for _ in range(10):
        if random.random() > loss_prob:
            client.send_data([round(random.uniform(20, 30), 2)])
        else:
            print("[Test] Simulated packet loss")
        time.sleep(client.reporting_interval)

def run_test_scenario(name, loss_prob=0.0, delay_mean=0.0, jitter=0.0):
    print(f"\n=== Running Test: {name} ===")
    client = SensorClient(device_id=random.randint(1000, 9999), reporting_interval=1)
    if delay_mean > 0:
        def delayed_send():
            for _ in range(10):
                delay = random.uniform(delay_mean - jitter, delay_mean + jitter)
                time.sleep(delay)
                client.send_data([round(random.uniform(20, 30), 2)])
        threading.Thread(target=delayed_send).start()
    else:
        simulate_loss(client, loss_prob)

if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    time.sleep(2)
    run_test_scenario("Baseline")
    run_test_scenario("Loss 5%", loss_prob=0.05)
    run_test_scenario("Delay + Jitter", delay_mean=0.1, jitter=0.01)
    print("\n✅ All tests complete. Check telemetry_log.csv for results.")

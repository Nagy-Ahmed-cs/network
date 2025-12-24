# scenario_client.py
# small helper usable by test runner; ensures local imports work when subprocessed

import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from client import SensorClient
import time
import random

# these defaults can be overridden by writing this file before launching (test runner does that)
DEVICE_ID = random.randint(1000, 9999)
REPORTING_INTERVAL = 1
DURATION = 10
LOSS_PROB = 0.0
BATCH = 1

if __name__ == "__main__":
    c = SensorClient(device_id=DEVICE_ID, reporting_interval=REPORTING_INTERVAL, batch_size=BATCH)
    start = time.time()
    while time.time() - start < DURATION:
        if random.random() > LOSS_PROB:
            c.send_data([round(random.uniform(20, 30), 2) for _ in range(BATCH)])
        else:
            # simulate loss by not sending
            print("[scenario_client] simulated loss")
        time.sleep(REPORTING_INTERVAL)
    c.running = False

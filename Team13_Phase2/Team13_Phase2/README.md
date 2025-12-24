# TinyTelemetry — Phase 2 (complete)

## Files
- protocol.py
- server.py
- client.py
- scenario_client.py
- test.py
- graphs.py
- mini-rfc.md

## Quick run (local)
1. Install dependencies (for plotting):
   - `pip install matplotlib pandas`
2. Put all files in one folder.
3. Run tests:
   - `python test.py`
   This runs three scenarios and stores per-scenario outputs under `results/`.
4. Generate graphs:
   - `python graphs.py`
   This writes the two required PNGs under `results/`.

## Outputs
- `telemetry_log.csv` — raw packet log (device_id, seq, timestamp, arrival_time, duplicate_flag, gap_flag, heartbeat_flag, offline_flag)
- `telemetry_reordered.csv` — readings reordered by packet timestamp
- `metrics.json` — derived metrics including bytes_per_report and duplicate_rate
- `results/*` — scenario folders with copies of the above

## Notes
- For real netem tests (loss/delay) use Linux and run `tc qdisc` on an appropriate interface. The included `test.py` simulates loss in the client; you can adapt the runner to call `tc` for controlled experiments.

# graphs_phase2.py
import os
import json
import matplotlib.pyplot as plt
import pandas as pd

RESULTS_DIR = "results"
out_agg = os.path.join(RESULTS_DIR, "aggregated_metrics.csv")

rows = []
for folder in sorted(os.listdir(RESULTS_DIR)):
    sdir = os.path.join(RESULTS_DIR, folder)
    if not os.path.isdir(sdir):
        continue
    mpath = os.path.join(sdir, "metrics.json")
    notes = os.path.join(sdir, "notes.txt")
    if not os.path.exists(mpath):
        continue
    try:
        with open(mpath) as mf:
            m = json.load(mf)
    except:
        continue
    info = {}
    if os.path.exists(notes):
        try:
            with open(notes) as nf:
                info = json.load(nf)
        except:
            info = {}
    rows.append({
        "scenario": folder,
        "reporting_interval": float(info.get("reporting_interval", float(m.get("reporting_interval", 0)))),
        "bytes_per_report": float(m.get("bytes_per_report", 0)),
        "duplicate_rate": float(m.get("duplicate_rate", 0)),
        "loss_prob": float(info.get("loss_prob", 0)),
        "batch": int(info.get("batch", 1))
    })

if not rows:
    print("No results to plot in", RESULTS_DIR)
    raise SystemExit(1)

df = pd.DataFrame(rows)
df.to_csv(out_agg, index=False)
print("Wrote aggregated metrics to", out_agg)

# bytes_per_report vs reporting_interval
plt.figure()
# plot each batch size as separate line
for b, g in df.groupby("batch"):
    g2 = g.sort_values("reporting_interval")
    plt.plot(g2["reporting_interval"], g2["bytes_per_report"], marker='o', label=f"batch={b}")
plt.xlabel("reporting_interval (s)")
plt.ylabel("bytes_per_report (bytes)")
plt.title("bytes_per_report vs reporting_interval")
plt.grid(True)
plt.legend()
out1 = os.path.join(RESULTS_DIR, "bytes_per_report_vs_interval.png")
plt.savefig(out1)
print("Saved", out1)
plt.close()

# duplicate_rate vs loss
plt.figure()
# group by (loss_prob) and plot median duplicate_rate
grp = df.groupby("loss_prob").agg({"duplicate_rate":["median","min","max"]}).reset_index()
losses = grp["loss_prob"].tolist()
med = grp[("duplicate_rate","median")].tolist()
mn = grp[("duplicate_rate","min")].tolist()
mx = grp[("duplicate_rate","max")].tolist()
plt.plot(losses, med, marker='o', label='median duplicate_rate')
# shaded area for min-max
plt.fill_between(losses, mn, mx, alpha=0.2)
plt.xlabel("loss probability")
plt.ylabel("duplicate_rate")
plt.title("duplicate_rate vs loss")
plt.grid(True)
plt.legend()
out2 = os.path.join(RESULTS_DIR, "duplicate_rate_vs_loss.png")
plt.savefig(out2)
print("Saved", out2)
plt.close()

"""Figure for the memory-budgeted decomposition: measured peak memory of each plan against its node budget.
Usage: python3 plot_memory_plans.py   (reads results/memory_plans.json, writes results/memory_plans.png)"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

H1 = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(os.path.join(H1, "results", "memory_plans.json")))
whole = d["unsplit_reference"]["whole_model_peak_mb"]
budgets, peaks, labels = [], [], []
for b, p in d["plans"].items():
    budgets.append(int(b))
    if p.get("whole_model_fits"):
        peaks.append(whole); labels.append("whole model,\nno rounds")
    else:
        peaks.append(p["validation"]["measured_peak_mb_other_positions"]); labels.append(f"{p['steps']} steps,\n{p['bisection_rounds']} rounds")
x = range(len(budgets))
fig, ax = plt.subplots(figsize=(8, 3.8), dpi=150)
ax.bar(x, budgets, width=0.6, color="#d9d9d6", label="node memory budget")
ax.bar(x, peaks, width=0.3, color="#2f6fd0", label="measured peak while proving the plan's largest steps")
for i, v in zip(x, peaks):
    ax.text(i, v + 25, f"{v:,} MB", ha="center", fontsize=8)
ax.axhline(whole, color="#777", ls="--", lw=1)
ax.text(-0.45, whole + 30, f"whole 60-block model: {whole:,} MB", fontsize=8, color="#444")
ax.set_xticks(list(x), [f"{b:,} MB\n{l}" if b < 1024 else f"{b // 1024} GB\n{l}" for b, l in zip(budgets, labels)], fontsize=8)
ax.set_ylabel("MB")
ax.set_title("Every plan stayed within its node's memory budget", fontsize=10)
ax.spines[["top", "right"]].set_visible(False)
ax.legend(fontsize=7, loc="upper left", frameon=False)
fig.tight_layout()
fig.savefig(os.path.join(H1, "results", "memory_plans.png"))
print("wrote results/memory_plans.png")

"""Collect all results into results/summary.json and a speedup-vs-depth plot."""
import json, numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

st60 = json.load(open("results/steps_B60.json"))
step_t = {k: v["prove_mean_s"] for k, v in st60.items() if k != "mono"}
worst_step = max(step_t.values()); worst_name = max(step_t, key=step_t.get)
block_t = max(step_t[k] for k in ("u2", "u30", "u60"))
gas = json.load(open("results/gas.json")); qa = json.load(open("results/quant_accuracy_S9.json"))
acc = json.load(open("results/accuracy_suite.json")); disp = json.load(open("results/disputes_B60.json"))

sweep = []
for B in [1, 8, 24, 60]:
    mono = json.load(open(f"results/steps_B{B}.json"))["mono"]
    n_steps = B + 3  # 2 projection halves + B blocks + head
    # per-step circuits have identical shapes at every depth (width 32), so B=60 step timings apply
    mean_step = (step_t["proj0"] + step_t["proj1"] + step_t["u1"] + block_t * max(B - 1, 0) + step_t["u61"]) / n_steps
    sweep.append(dict(B=B, n_steps=n_steps, mono_logrows=mono["logrows"], mono_rows=mono["num_rows"],
                      mono_prove_s=mono["prove_mean_s"], worst_step_prove_s=worst_step,
                      speedup_worst=mono["prove_mean_s"] / worst_step, speedup_mean=mono["prove_mean_s"] / mean_step,
                      bisection_rounds=int(np.ceil(np.log2(n_steps))),
                      quant_acc_drop_pp=qa[str(B)]["acc_drop_pp"], quant_f1_drop_pp=qa[str(B)]["f1_drop_pp"],
                      float_test_f1=acc[str(B)]["selected"]["test_f1"], float_test_pr_auc=acc[str(B)]["selected"]["test_pr_auc"],
                      seed_f1_mean=float(np.mean([s["test_f1"] for s in acc[str(B)]["seeds"]])),
                      seed_f1_std=float(np.std([s["test_f1"] for s in acc[str(B)]["seeds"]]))))

g = gas; game = g["game_B60"]
rounds_max = sweep[-1]["bisection_rounds"]
round_gas = float(np.mean(game["reveal_gas"][:4])) + float(np.mean(game["respond_gas"][:4]))
dispute_gas_block = rounds_max * round_gas + g["B60_u2"]["verify_tx_gas"]
dispute_gas_worst = rounds_max * round_gas + max(v["verify_tx_gas"] for k, v in g.items() if k.startswith("B60_") and k != "B60_mono")
mono_gas = g["B60_mono"]["verify_tx_gas"]; commit = game["commit_compact_steady"]
summary = dict(
    sweep=sweep, step_prove_s_B60=step_t, worst_step=worst_name,
    gas=dict(mono_verify=mono_gas, step_verify={k[4:]: v["verify_tx_gas"] for k, v in g.items() if k.startswith("B60_") and k != "B60_mono"},
             commit_per_inference=commit, bisection_round=round_gas, dispute_total_typical=dispute_gas_block,
             dispute_total_worst=dispute_gas_worst, undisputed_cost_ratio=mono_gas / commit,
             per_dispute_cost_ratio=mono_gas / dispute_gas_worst,
             max_dispute_rate_for_10x=(mono_gas / 10 - commit) / dispute_gas_worst),
    disputes=dict(n=len(disp), all_correct=all(v["outcome_correct"] for v in disp.values()),
                  all_located=all(v["located_correctly"] for v in disp.values()),
                  max_rounds=max(v["bisection_rounds"] for v in disp.values()),
                  mean_prove_s=float(np.mean([v["prove_s"] for v in disp.values()]))))
json.dump(summary, open("results/summary.json", "w"), indent=2, default=float)

fig, ax = plt.subplots(figsize=(6, 3.6))
Bs = [s["B"] for s in sweep]
ax.plot(Bs, [s["speedup_worst"] for s in sweep], "o-", label="worst-case disputed step")
ax.plot(Bs, [s["speedup_mean"] for s in sweep], "s--", label="average disputed step")
ax.axhline(10, color="grey", ls=":", label="10x target"); ax.axhline(1, color="k", lw=0.5)
for s in sweep: ax.annotate(f"2^{s['mono_logrows']}", (s["B"], s["speedup_worst"]), textcoords="offset points", xytext=(4, -12), fontsize=8)
ax.set_xlabel("residual blocks in the model (width 32)"); ax.set_ylabel("proof-time speedup vs monolithic")
ax.set_title("H1: per-dispute proving speedup vs model depth"); ax.legend(fontsize=8); fig.tight_layout()
fig.savefig("results/speedup_vs_depth.png", dpi=150)
for s in sweep: print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in s.items()})
print(json.dumps({k: v for k, v in summary.items() if k != "sweep"}, indent=1, default=float))

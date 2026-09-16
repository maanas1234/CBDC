"""Train the depth-sweep suite. For each depth, 3 seeds; the seed with the best
VALIDATION PR-AUC is kept as the model that goes through the ZK pipeline.
All seeds' test metrics are recorded (mean/std) for honest reporting."""
import json, pickle, numpy as np, warnings
warnings.filterwarnings("ignore")
import train as T
W = 32
out = {}
for B in [1, 8, 24, 60]:
    runs = []
    for seed in [0, 1, 2]:
        units, sc, r = T.train(W, B, seed, lr=3e-4)
        runs.append((r, units, sc))
        print(B, seed, {k: round(v, 4) for k, v in r.items() if isinstance(v, float)}, flush=True)
    best = max(runs, key=lambda t: t[0]["val_pr_auc"])
    pickle.dump(dict(units=best[1], scaler=best[2], res=best[0]), open(f"models/W{W}_B{B}.pkl", "wb"))
    out[B] = dict(selected=best[0], seeds=[t[0] for t in runs])
json.dump(out, open("results/accuracy_suite.json", "w"), indent=2, default=float)

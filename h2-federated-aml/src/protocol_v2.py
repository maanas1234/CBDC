"""H2 protocol v2: matched training budget, validation-based model selection, pooled
centralized baseline, false-positive outcome, 10 seeds, and an institution-level DP sweep.

Usage:
    python src/protocol_v2.py run --config experiments/configs/protocol_v2.yaml --seed 42
    python src/protocol_v2.py aggregate --config experiments/configs/protocol_v2.yaml
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import yaml
from scipy.stats import wilcoxon

from data import RESULTS_DIR, load_graph, make_splits
from dp_accounting import epsilon_for
from federated import run_centralized_pooled, run_federated, run_local_only


def _row(metrics: dict, **fields) -> dict:
    (tn, fp), (fn, tp) = metrics["confusion_matrix"]
    out = {key: value for key, value in metrics.items() if key != "confusion_matrix"}
    out.update(false_positives=fp, false_negatives=fn, true_positives=tp, true_negatives=tn, **fields)
    return out


def _case(data, splits, cfg, seed, k, scarcity, method, boundary_lambda=0.0, privacy=None):
    common = dict(k=k, partition_method=cfg["partition_method"], seed=seed, lr=cfg["learning_rate"], hidden_dim=cfg["hidden_dim"], device=cfg["device"], scarcity=scarcity, select_on_val=True)
    budget = cfg["global_rounds"] * cfg["local_epochs"]
    if method == "centralized":
        metrics, *_ = run_centralized_pooled(data, splits, epochs=budget, **common)
    elif method == "local_only":
        metrics, *_ = run_local_only(data, splits, epochs=budget, **common)
    else:
        metrics, *_ = run_federated(data, splits, rounds=cfg["global_rounds"], local_epochs=cfg["local_epochs"], boundary_lambda=boundary_lambda, privacy=privacy, **common)
    return metrics


def run_seed(cfg: dict, seed: int, out_dir: Path) -> Path:
    torch.set_num_threads(int(cfg.get("threads_per_worker", 3)))
    data = load_graph(); splits = make_splits(data.y, seed); rows = []; k = cfg["institutions"]
    for scarcity in cfg["scarcity_levels"]:
        for method in ("centralized", "local_only", "fedavg", "fedavg_boundary"):
            lam = cfg["boundary_lambda"] if method == "fedavg_boundary" else 0.0
            rows.append(_row(_case(data, splits, cfg, seed, k, scarcity, method, lam), experiment="main_scarcity", method=method, scarcity=scarcity, seed=seed, institutions=k, boundary_lambda=lam))
    for lam in cfg["lambda_values"]:
        rows.append(_row(_case(data, splits, cfg, seed, k, cfg["lambda_ablation_scarcity"], "fedavg_boundary", lam), experiment="lambda_ablation", method="fedavg_boundary", scarcity=cfg["lambda_ablation_scarcity"], seed=seed, institutions=k, boundary_lambda=lam))
    for kk in cfg["institution_counts"]:
        for method in ("centralized", "local_only", "fedavg"):
            rows.append(_row(_case(data, splits, cfg, seed, kk, cfg["institution_ablation_scarcity"], method), experiment="institution_count_ablation", method=method, scarcity=cfg["institution_ablation_scarcity"], seed=seed, institutions=kk, boundary_lambda=0.0))
    dp = cfg["privacy_sweep"]
    for z in dp["noise_multipliers"]:
        privacy = {"enabled": True, "clip_norm": dp["clip_norm"], "noise_multiplier": z}
        eps = epsilon_for(cfg["global_rounds"], z, dp["delta"])
        rows.append(_row(_case(data, splits, cfg, seed, k, dp["scarcity"], "fedavg", 0.0, privacy), experiment="privacy_sweep", method="fedavg_dp", scarcity=dp["scarcity"], seed=seed, institutions=k, boundary_lambda=0.0, clip_norm=dp["clip_norm"], noise_multiplier=z, epsilon=eps, delta=dp["delta"]))
    out_dir.mkdir(parents=True, exist_ok=True); path = out_dir / f"seed_{seed}.csv"
    pd.DataFrame(rows).to_csv(path, index=False); return path


def _paired(a: pd.Series, b: pd.Series, alternative: str) -> tuple[int, float, float]:
    paired = a.index.intersection(b.index); diff = (a.loc[paired] - b.loc[paired]).astype(float)
    if len(diff) < 2: return len(diff), float("nan"), float("nan")
    p = 1.0 if (diff == 0).all() else float(wilcoxon(diff, alternative=alternative, zero_method="wilcox").pvalue)
    return len(diff), float(diff.mean()), p


def _holm(pvalues: list[float]) -> list[float]:
    order = np.argsort(pvalues); m = len(pvalues); adjusted = [0.0] * m; running = 0.0
    for rank, idx in enumerate(order):
        running = max(running, min(1.0, (m - rank) * pvalues[idx])); adjusted[idx] = running
    return adjusted


def aggregate(cfg: dict, out_dir: Path) -> dict:
    frames = [pd.read_csv(p) for p in sorted(out_dir.glob("seed_*.csv"))]
    if not frames: raise FileNotFoundError(f"no seed results in {out_dir}")
    results = pd.concat(frames, ignore_index=True); results.to_csv(out_dir / "all_results.csv", index=False)
    seeds = sorted(results.seed.unique())
    metric_cols = ["f1", "pr_auc", "roc_auc", "precision", "recall", "false_positives", "false_negatives"]
    keys = ["experiment", "method", "scarcity", "institutions", "boundary_lambda"] + (["noise_multiplier"] if "noise_multiplier" in results else [])
    summary = results.groupby(keys, dropna=False)[metric_cols].agg(["mean", "std"]); summary.columns = [f"{m}_{s}" for m, s in summary.columns]
    summary.reset_index().to_csv(out_dir / "summary.csv", index=False)

    main = results[results.experiment == "main_scarcity"]
    def series(method, scarcity, metric):
        return main[(main.method == method) & (main.scarcity == scarcity)].set_index("seed")[metric]

    # Primary (pre-registered): federated vs centralized false positives, one-sided, Holm across scarcity levels.
    primary = []
    for s in cfg["scarcity_levels"]:
        fp_c, fp_f = series("centralized", s, "false_positives"), series("fedavg", s, "false_positives")
        n, mean_diff, p = _paired(fp_f, fp_c, "less")
        mean_c, mean_f = float(fp_c.mean()), float(fp_f.mean())
        reduction = (mean_c - mean_f) / mean_c if mean_c > 0 else float("nan")
        primary.append({"scarcity": s, "n_seeds": n, "fp_centralized_mean": mean_c, "fp_fedavg_mean": mean_f, "fp_reduction": reduction, "p_one_sided": p})
    adjusted = _holm([row["p_one_sided"] if not math.isnan(row["p_one_sided"]) else 1.0 for row in primary])
    for row, adj in zip(primary, adjusted):
        row["p_holm"] = adj
        row["criterion_met"] = bool(row["fp_reduction"] >= cfg["criterion"]["min_fp_reduction"] and adj < cfg["criterion"]["alpha"])
    pd.DataFrame(primary).to_csv(out_dir / "h2_primary_fp_criterion.csv", index=False)

    # Secondary (exploratory): two-sided comparisons on F1, PR-AUC and false positives.
    secondary = []
    for s in cfg["scarcity_levels"]:
        for first, second in (("fedavg", "centralized"), ("fedavg", "local_only"), ("fedavg_boundary", "fedavg")):
            for metric in ("f1", "pr_auc", "false_positives"):
                n, mean_diff, p = _paired(series(first, s, metric), series(second, s, metric), "two-sided")
                secondary.append({"scarcity": s, "comparison": f"{first} - {second}", "metric": metric, "n_seeds": n, "mean_difference": mean_diff, "p_two_sided": p})
    pd.DataFrame(secondary).to_csv(out_dir / "h2_secondary_comparisons.csv", index=False)

    # Refined H2 (exploratory): does the boundary channel reduce F1 degradation under scarcity?
    refined = []
    for s in cfg["scarcity_levels"]:
        if s == 1.0: continue
        deg_f = series("fedavg", 1.0, "f1") - series("fedavg", s, "f1"); deg_b = series("fedavg_boundary", 1.0, "f1") - series("fedavg_boundary", s, "f1")
        n, mean_diff, p = _paired(deg_b, deg_f, "less")
        refined.append({"scarcity": s, "n_seeds": n, "degradation_fedavg_mean": float(deg_f.mean()), "degradation_boundary_mean": float(deg_b.mean()), "mitigation_mean": -mean_diff, "p_one_sided": p})
    pd.DataFrame(refined).to_csv(out_dir / "h2_refined_boundary_mitigation.csv", index=False)

    privacy = results[results.experiment == "privacy_sweep"]
    if not privacy.empty:
        p = privacy.groupby(["noise_multiplier"]).agg(epsilon=("epsilon", "first"), f1_mean=("f1", "mean"), f1_std=("f1", "std"), pr_auc_mean=("pr_auc", "mean"), fp_mean=("false_positives", "mean")).reset_index()
        p.to_csv(out_dir / "h2_privacy_tradeoff.csv", index=False)

    report = {"seeds": [int(s) for s in seeds], "n_seeds": len(seeds), "primary": primary}
    (out_dir / "report.json").write_text(json.dumps(report, indent=2, default=float), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(); sub = parser.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run"); r.add_argument("--config", required=True); r.add_argument("--seed", type=int, required=True)
    a = sub.add_parser("aggregate"); a.add_argument("--config", required=True)
    args = parser.parse_args(); cfg = yaml.safe_load(open(args.config, encoding="utf-8")); out_dir = RESULTS_DIR / cfg["results_subdir"]
    if args.cmd == "run": print(run_seed(cfg, args.seed, out_dir))
    else: print(json.dumps(aggregate(cfg, out_dir), indent=2, default=float))


if __name__ == "__main__":
    main()

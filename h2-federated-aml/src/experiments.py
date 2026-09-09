"""H2 comparison matrix, ablations, CSV result tables, and six figures."""
from __future__ import annotations
from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd
import yaml
from data import RESULTS_DIR, load_graph, make_splits
from federated import run_federated, run_local_only

METHODS = (("local_only", None), ("fedavg", 0.0), ("fedavg_boundary", "configured"))


def _run_case(data, splits, config, seed, institution_count, scarcity, method, boundary_lambda):
    common = dict(k=institution_count, partition_method=config["partition_method"], seed=seed, lr=config["learning_rate"], hidden_dim=config["hidden_dim"], device=config["device"], scarcity=scarcity)
    if method == "local_only": metrics, institutions, _, counts = run_local_only(data, splits, epochs=config["global_rounds"] * config["local_epochs"], **common)
    else: metrics, institutions, _, _, counts = run_federated(data, splits, rounds=config["global_rounds"], local_epochs=config["local_epochs"], boundary_lambda=boundary_lambda, **common)
    row = {**metrics, "method": method, "scarcity": float(scarcity), "seed": seed, "institutions": institution_count, "lambda": float(boundary_lambda or 0.0), "partition_method": config["partition_method"]}
    for count in counts: count.update({"method": method, "seed": seed, "institutions": institution_count, "partition_method": config["partition_method"]})
    return row, institutions, counts


def _add_degradation(results: pd.DataFrame) -> pd.DataFrame:
    results = results.copy(); baseline = results[results["scarcity"] == 1.0].set_index(["experiment", "method", "seed", "institutions"])["f1"]
    results["degradation_f1"] = [baseline.get((row.experiment, row.method, row.seed, row.institutions), float("nan")) - row.f1 for row in results.itertuples()]
    return results


def _make_figures(results: pd.DataFrame, stats: pd.DataFrame, figures: Path) -> None:
    for metric, filename, ylabel in (("f1", "f1_vs_label_scarcity.png", "F1"), ("pr_auc", "pr_auc_vs_label_scarcity.png", "PR-AUC"), ("degradation_f1", "degradation_vs_label_scarcity.png", "F1 degradation")):
        axis = results.groupby(["method", "scarcity"])[metric].mean().unstack(0).sort_index().plot(marker="o")
        axis.set_xscale("log"); axis.set_xlabel("available labelled illicit training fraction"); axis.set_ylabel(ylabel); axis.figure.tight_layout(); axis.figure.savefig(figures / filename, dpi=160); plt.close(axis.figure)
    axis = results.groupby(["method", "scarcity"])["f1"].mean().unstack(0).sort_index().plot(marker="o")
    axis.set_xscale("log"); axis.set_xlabel("available labelled illicit training fraction"); axis.set_ylabel("F1"); axis.figure.tight_layout(); axis.figure.savefig(figures / "performance_vs_label_scarcity.png", dpi=160); plt.close(axis.figure)
    if not stats.empty:
        stats = stats[stats["institutions"] == stats["institutions"].max()].set_index("institution")
        axis = stats[["illicit_nodes", "licit_nodes"]].plot(kind="bar", stacked=True); axis.figure.tight_layout(); axis.figure.savefig(figures / "institution_label_distribution.png", dpi=160); plt.close(axis.figure)
        axis = stats[["boundary_nodes", "cross_institution_edges"]].plot(kind="bar"); axis.figure.tight_layout(); axis.figure.savefig(figures / "boundary_connectivity.png", dpi=160); plt.close(axis.figure)


def write_outputs(main_results, lambda_results, institution_results, scarcity_counts, institution_stats, results_dir=RESULTS_DIR) -> None:
    """Write measured H2 records, never fabricated placeholder metrics."""
    results_dir = Path(results_dir); figures = results_dir / "figures"; figures.mkdir(parents=True, exist_ok=True)
    main_results = _add_degradation(main_results); lambda_results = _add_degradation(lambda_results) if not lambda_results.empty else lambda_results; institution_results = _add_degradation(institution_results) if not institution_results.empty else institution_results
    main_results.to_csv(results_dir / "scarcity_results.csv", index=False); main_results[main_results["method"] == "fedavg_boundary"].to_csv(results_dir / "boundary_results.csv", index=False); main_results[(main_results["method"] == "fedavg") & (main_results["scarcity"] == 1.0)].to_csv(results_dir / "federated_results.csv", index=False)
    lambda_results.to_csv(results_dir / "lambda_ablation_results.csv", index=False); institution_results.to_csv(results_dir / "institution_count_ablation_results.csv", index=False)
    pd.concat([main_results, lambda_results, institution_results], ignore_index=True).to_csv(results_dir / "ablation_results.csv", index=False)
    pd.DataFrame(scarcity_counts).to_csv(results_dir / "per_institution_scarcity_counts.csv", index=False); pd.DataFrame(institution_stats).drop_duplicates().to_csv(results_dir / "institution_stats.csv", index=False)
    _make_figures(main_results, pd.DataFrame(institution_stats), figures)


def run(config: dict) -> None:
    data = load_graph(); main_rows, lambda_rows, institution_rows, scarcity_counts, institution_stats = [], [], [], [], []; main_k = config["institutions"]
    for seed in config["seeds"]:
        splits = make_splits(data.y, seed)
        for scarcity in config["scarcity_levels"]:
            for method, lam in METHODS:
                resolved = config["boundary_lambda"] if lam == "configured" else lam; row, institutions, counts = _run_case(data, splits, config, seed, main_k, scarcity, method, resolved)
                row["experiment"] = "main_scarcity"; main_rows.append(row)
                if method == "local_only": scarcity_counts.extend([{**count, "experiment": "main_scarcity"} for count in counts])
                institution_stats.extend([{**institution.stats, "institutions": main_k, "seed": seed, "partition_method": config["partition_method"]} for institution in institutions])
        for lam in config["lambda_values"]:
            row, institutions, counts = _run_case(data, splits, config, seed, main_k, config["lambda_ablation_scarcity"], "fedavg_boundary", lam); row["experiment"] = "lambda_ablation"; lambda_rows.append(row); scarcity_counts.extend([{**count, "experiment": "lambda_ablation"} for count in counts])
        for k in config["institution_counts"]:
            for method, lam in METHODS:
                resolved = config["boundary_lambda"] if lam == "configured" else lam; row, institutions, counts = _run_case(data, splits, config, seed, k, config["institution_ablation_scarcity"], method, resolved)
                row["experiment"] = "institution_count_ablation"; institution_rows.append(row)
                if method == "local_only": scarcity_counts.extend([{**count, "experiment": "institution_count_ablation"} for count in counts])
                institution_stats.extend([{**institution.stats, "institutions": k, "seed": seed, "partition_method": config["partition_method"]} for institution in institutions])
    write_outputs(pd.DataFrame(main_rows), pd.DataFrame(lambda_rows), pd.DataFrame(institution_rows), scarcity_counts, institution_stats)


def run_config(config_path: str | Path) -> None:
    with open(config_path, encoding="utf-8") as handle: run(yaml.safe_load(handle))

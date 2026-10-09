"""Seed aggregation and matched paired significance tests."""
from __future__ import annotations
import pandas as pd
from scipy.stats import wilcoxon


def summarize_results(results: pd.DataFrame) -> pd.DataFrame:
    if results.empty:
        return pd.DataFrame()
    keys = [column for column in ("experiment", "method", "scarcity", "institutions", "lambda", "partition_method") if column in results]
    metrics = [column for column in results.select_dtypes(include="number").columns if column not in {"seed", *keys}]
    grouped = results.groupby(keys, dropna=False)[metrics].agg(["mean", "std"])
    grouped.columns = [f"{metric}_{stat}" for metric, stat in grouped.columns]
    return grouped.reset_index()


def paired_significance(results: pd.DataFrame, alpha: float = 0.05) -> pd.DataFrame:
    comparisons = (("local_only", "fedavg"), ("fedavg_boundary", "fedavg"))
    subset = results[results["experiment"] == "main_scarcity"] if not results.empty and "experiment" in results else results
    metrics = [metric for metric in ("f1", "pr_auc", "roc_auc", "accuracy", "precision", "recall") if metric in subset]
    group_cols = [column for column in ("scarcity", "institutions", "partition_method") if column in subset]
    rows = []
    for condition, group in subset.groupby(group_cols, dropna=False) if not subset.empty else []:
        condition = condition if isinstance(condition, tuple) else (condition,)
        values = dict(zip(group_cols, condition))
        for first, second in comparisons:
            a, b = group[group.method == first].set_index("seed"), group[group.method == second].set_index("seed")
            paired = a.index.intersection(b.index).sort_values()
            for metric in metrics:
                differences = (a.loc[paired, metric] - b.loc[paired, metric]).dropna()
                if len(differences) < 2:
                    continue
                p_value = 1.0 if (differences == 0).all() else float(wilcoxon(differences, alternative="two-sided", zero_method="wilcox").pvalue)
                rows.append({**values, "comparison": f"{first} vs {second}", "metric": metric, "n_paired_seeds": len(differences), "mean_difference_first_minus_second": float(differences.mean()), "effect_direction": "first_higher" if differences.mean() > 0 else "second_higher" if differences.mean() < 0 else "no_difference", "p_value": p_value, "alpha": alpha, "statistically_significant": p_value < alpha, "test": "paired two-sided Wilcoxon signed-rank"})
    return pd.DataFrame(rows)

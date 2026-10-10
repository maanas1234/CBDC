"""Agent-level re-analysis of the control-vs-treatment experiment.

The action-level two-proportion z-test treats every action as independent, but each agent
contributes many correlated actions (pseudo-replication). Here the unit of analysis is the
agent: one violation rate per agent, compared between groups. Stdlib only.
"""
from __future__ import annotations

import csv
import math
import random
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

from h3_abt.stats import standard_normal_cdf


@dataclass(frozen=True)
class AgentLevelResult:
    n_control_agents: int
    n_treatment_agents: int
    control_mean_rate: float
    treatment_mean_rate: float
    mean_difference: float
    mann_whitney_u: float
    mann_whitney_z: float
    mann_whitney_p_one_sided: float
    permutation_p_one_sided: float
    permutations: int
    permutation_seed: int
    majority_bar_treatment: int
    majority_bar_control: int


def per_agent_rates(rows: list[dict]) -> dict[str, list[float]]:
    actions: dict[tuple[str, str], int] = defaultdict(int)
    violations: dict[tuple[str, str], int] = defaultdict(int)
    for row in rows:
        key = (row["group"], row["agent_id"])
        actions[key] += 1
        violations[key] += str(row["is_violation"]).strip().lower() == "true"
    rates: dict[str, list[float]] = defaultdict(list)
    for (group, agent), n in sorted(actions.items()):
        rates[group].append(violations[(group, agent)] / n)
    return dict(rates)


def mann_whitney_less(treatment: list[float], control: list[float]) -> tuple[float, float, float]:
    """U statistic for treatment, normal approximation with tie correction.

    One-sided p for H1: treatment values tend to be lower than control values.
    """
    pooled = sorted([(v, 0) for v in treatment] + [(v, 1) for v in control])
    ranks = [0.0] * len(pooled)
    tie_term = 0.0
    i = 0
    while i < len(pooled):
        j = i
        while j + 1 < len(pooled) and pooled[j + 1][0] == pooled[i][0]:
            j += 1
        average = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[k] = average
        t = j - i + 1
        tie_term += t ** 3 - t
        i = j + 1
    n1, n2 = len(treatment), len(control)
    rank_sum_treatment = sum(r for r, (_, g) in zip(ranks, pooled) if g == 0)
    u = rank_sum_treatment - n1 * (n1 + 1) / 2
    n = n1 + n2
    variance = n1 * n2 / 12 * ((n + 1) - tie_term / (n * (n - 1)))
    z = (u - n1 * n2 / 2) / math.sqrt(variance) if variance > 0 else 0.0
    return u, z, standard_normal_cdf(z)


def permutation_less(treatment: list[float], control: list[float], permutations: int, seed: int) -> float:
    """Monte Carlo p for H1: mean(treatment) - mean(control) is this low by chance.

    Uses the (count + 1) / (permutations + 1) estimator, so p is never reported as zero.
    """
    observed = sum(treatment) / len(treatment) - sum(control) / len(control)
    pooled = treatment + control
    n1 = len(treatment)
    rng = random.Random(seed)
    at_least_as_extreme = 0
    for _ in range(permutations):
        rng.shuffle(pooled)
        diff = sum(pooled[:n1]) / n1 - sum(pooled[n1:]) / (len(pooled) - n1)
        if diff <= observed + 1e-12:
            at_least_as_extreme += 1
    return (at_least_as_extreme + 1) / (permutations + 1)


def analyze(rows: list[dict], permutations: int = 100_000, seed: int = 42) -> AgentLevelResult:
    rates = per_agent_rates(rows)
    control, treatment = rates["control"], rates["treatment"]
    u, z, p_mw = mann_whitney_less(treatment, control)
    return AgentLevelResult(
        n_control_agents=len(control),
        n_treatment_agents=len(treatment),
        control_mean_rate=sum(control) / len(control),
        treatment_mean_rate=sum(treatment) / len(treatment),
        mean_difference=sum(treatment) / len(treatment) - sum(control) / len(control),
        mann_whitney_u=u,
        mann_whitney_z=z,
        mann_whitney_p_one_sided=p_mw,
        permutation_p_one_sided=permutation_less(list(treatment), list(control), permutations, seed),
        permutations=permutations,
        permutation_seed=seed,
        majority_bar_treatment=sum(rate <= 0.5 for rate in treatment),
        majority_bar_control=sum(rate <= 0.5 for rate in control),
    )


def analyze_csv(path: str | Path, permutations: int = 100_000, seed: int = 42) -> AgentLevelResult:
    with open(path, newline="", encoding="utf-8") as handle:
        return analyze(list(csv.DictReader(handle)), permutations, seed)


def to_dict(result: AgentLevelResult) -> dict:
    return asdict(result)

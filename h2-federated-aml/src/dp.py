"""Client-level differential privacy for FedAvg: clipped updates, Gaussian noise, RDP accounting.

Guarantee: each institution (client) is protected, not each transaction record.
Assumes all institutions participate in every round (no subsampling amplification).
"""
from __future__ import annotations
import math
from collections import OrderedDict

import torch


def clip_update(delta: OrderedDict, clip: float) -> OrderedDict:
    norm = torch.sqrt(sum((value.double() ** 2).sum() for value in delta.values() if torch.is_floating_point(value)))
    factor = min(1.0, clip / float(norm)) if float(norm) > 0 else 1.0
    return OrderedDict((key, value * factor if torch.is_floating_point(value) else value) for key, value in delta.items())


def dp_aggregate(global_state: OrderedDict, local_states: list[OrderedDict], clip: float, noise_multiplier: float, generator: torch.Generator) -> OrderedDict:
    """Uniform-weight average of clipped deltas plus Gaussian noise. Sensitivity of the sum is clip, so the average has sensitivity clip / K."""
    count = len(local_states); total = OrderedDict()
    for key in global_state:
        if torch.is_floating_point(global_state[key]): total[key] = torch.zeros_like(global_state[key], dtype=torch.double)
    for local in local_states:
        delta = OrderedDict((key, local[key].detach().cpu().double() - global_state[key].detach().cpu().double()) for key in global_state if torch.is_floating_point(global_state[key]))
        clipped = clip_update(delta, clip)
        for key in total: total[key] += clipped[key]
    result = OrderedDict()
    for key in global_state:
        if not torch.is_floating_point(global_state[key]): result[key] = global_state[key].detach().cpu().clone(); continue
        noise = torch.randn(total[key].shape, generator=generator, dtype=torch.double) * (noise_multiplier * clip / count)
        mean_update = total[key] / count + noise
        result[key] = (global_state[key].detach().cpu().double() + mean_update).to(global_state[key].dtype)
    return result


def rdp_epsilon(rounds: int, noise_multiplier: float, delta: float, orders: range | list[float] | None = None) -> float:
    """(epsilon, delta)-DP after `rounds` full-participation Gaussian releases, via RDP.

    Per-round RDP of the Gaussian mechanism at order a is a / (2 z^2). Composition adds across rounds.
    Conversion: eps = min_a [ T*a/(2 z^2) + log(1/delta) / (a - 1) ].
    """
    if rounds <= 0: return 0.0
    if noise_multiplier <= 0: return math.inf
    grid = orders if orders is not None else [1 + x / 10 for x in range(1, 2000)]
    return min(rounds * a / (2 * noise_multiplier ** 2) + math.log(1 / delta) / (a - 1) for a in grid)

"""Privacy accounting for the institution-level Gaussian mechanism in privacy.py.

Mechanism: every round, each institution clips its model update to L2 norm C and adds
independent N(0, (z*C)^2) noise before the server averages. Each institution's released
update is therefore a Gaussian mechanism with L2 sensitivity C and noise multiplier z.

Guarantee covered: institution-level (add/remove one institution's contribution), model-update
channel only, full participation every round (no subsampling amplification). It does NOT
cover per-transaction privacy, the boundary-embedding channel, or the sample-count weights
used by weighted FedAvg.
"""
from __future__ import annotations
import math


def gaussian_rdp(order: float, noise_multiplier: float) -> float:
    """Renyi DP of one Gaussian release with sensitivity 1 and std noise_multiplier."""
    return order / (2.0 * noise_multiplier ** 2)


def epsilon_for(rounds: int, noise_multiplier: float, delta: float = 1e-5) -> float:
    """(epsilon, delta) after `rounds` composed releases.

    Converts composed RDP with the standard bound eps = rdp + log(1/delta)/(order-1),
    minimized over a fine grid of orders.
    """
    if rounds <= 0:
        return 0.0
    if noise_multiplier <= 0:
        return math.inf
    orders = [1.0 + i / 100.0 for i in range(1, 100)] + [2.0 + i / 10.0 for i in range(0, 9981)]
    return min(rounds * gaussian_rdp(a, noise_multiplier) + math.log(1.0 / delta) / (a - 1.0) for a in orders)

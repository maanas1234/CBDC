import math
from collections import OrderedDict

import torch

from dp import clip_update, dp_aggregate, rdp_epsilon


def test_clip_update_bounds_norm():
    delta = OrderedDict(w=torch.tensor([3.0, 4.0]), b=torch.tensor([0.0]))
    clipped = clip_update(delta, 1.0)
    norm = torch.sqrt(sum((v ** 2).sum() for v in clipped.values()))
    assert math.isclose(float(norm), 1.0, rel_tol=1e-6)


def test_clip_update_leaves_small_norm_unchanged():
    delta = OrderedDict(w=torch.tensor([0.1, 0.1]))
    assert torch.allclose(clip_update(delta, 10.0)["w"], delta["w"])


def test_dp_aggregate_without_noise_is_mean_of_clipped_deltas():
    gen = torch.Generator().manual_seed(0)
    g = OrderedDict(w=torch.zeros(2))
    locals_ = [OrderedDict(w=torch.tensor([1.0, 0.0])), OrderedDict(w=torch.tensor([0.0, 1.0]))]
    out = dp_aggregate(g, locals_, clip=10.0, noise_multiplier=0.0, generator=gen)
    assert torch.allclose(out["w"], torch.tensor([0.5, 0.5]))


def test_rdp_epsilon_grows_with_rounds_and_shrinks_with_noise():
    e10 = rdp_epsilon(10, 1.0, 1e-5)
    assert rdp_epsilon(20, 1.0, 1e-5) > e10
    assert rdp_epsilon(10, 2.0, 1e-5) < e10


def test_rdp_epsilon_zero_rounds_is_zero_and_no_noise_is_infinite():
    assert rdp_epsilon(0, 1.0, 1e-5) == 0.0
    assert rdp_epsilon(5, 0.0, 1e-5) == math.inf

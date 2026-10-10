"""Institution-level update perturbation utilities (Gaussian mechanisms)."""
from __future__ import annotations

from collections import OrderedDict
import math
import torch


def privatize_model_update(global_state: dict, local_state: dict, clip_norm: float, noise_multiplier: float, *, generator=None):
    """Clip one institution's complete model delta, then add Gaussian noise.

    The returned state is global_state + clipped/noised local delta. It does not
    alter the local optimization objective. Parameters are flattened jointly so
    clipping is at the institution/update level rather than per example.
    """
    if clip_norm <= 0 or noise_multiplier < 0:
        raise ValueError("clip_norm must be positive and noise_multiplier non-negative")
    keys = [key for key, value in global_state.items() if torch.is_floating_point(value)]
    if not keys:
        return OrderedDict((key, value.detach().cpu().clone()) for key, value in local_state.items())
    deltas = [local_state[key].detach().cpu().float() - global_state[key].detach().cpu().float() for key in keys]
    norm = torch.sqrt(sum(torch.sum(delta * delta) for delta in deltas))
    scale = min(1.0, clip_norm / max(float(norm), 1e-12))
    result = OrderedDict()
    for key, base in global_state.items():
        base = base.detach().cpu().clone()
        if key in keys:
            delta = local_state[key].detach().cpu().float() - base.float()
            delta = delta * scale
            if noise_multiplier:
                delta = delta + torch.randn(delta.shape, generator=generator) * (clip_norm * noise_multiplier)
            result[key] = base.float() + delta
        else:
            result[key] = local_state[key].detach().cpu().clone()
    return result


def privatize_boundary_payload(payload, clip_norm: float, noise_multiplier: float, *, generator=None):
    """Return a payload with row-clipped/noised embeddings; IDs remain visible."""
    from boundary import BoundaryPayload, validate_no_raw_data
    if clip_norm <= 0 or noise_multiplier < 0:
        raise ValueError("clip_norm must be positive and noise_multiplier non-negative")
    vectors = payload.embeddings.detach().cpu().float().clone()
    norms = torch.linalg.vector_norm(vectors, dim=1, keepdim=True).clamp_min(1e-12)
    vectors = vectors * torch.clamp(clip_norm / norms, max=1.0)
    if noise_multiplier:
        vectors += torch.randn(vectors.shape, generator=generator) * (clip_norm * noise_multiplier)
    protected = BoundaryPayload(payload.node_ids.detach().cpu().clone(), vectors)
    validate_no_raw_data(protected)
    return protected

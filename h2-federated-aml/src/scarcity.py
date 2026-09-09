"""Deterministic train-only labelled-illicit scarcity controls."""
from __future__ import annotations
import torch
SCARCITY_LEVELS = (1.0, .5, .2, .1, .05, .01)


def apply_illicit_scarcity(train_mask: torch.Tensor, labels: torch.Tensor, fraction: float, seed: int) -> torch.Tensor:
    if not 0 < fraction <= 1: raise ValueError("fraction must be in (0, 1]")
    result = train_mask.clone(); illicit = torch.where(train_mask & (labels == 1))[0]; keep_n = max(1, round(len(illicit) * fraction)) if len(illicit) else 0
    kept = illicit[torch.randperm(len(illicit), generator=torch.Generator().manual_seed(seed))[:keep_n]] if keep_n else illicit
    result[illicit] = False; result[kept] = True; return result


def apply_institutional_illicit_scarcity(train_mask, labels, institutions, fraction, seed):
    result = train_mask.clone(); counts = []
    for institution in institutions:
        local_train = torch.zeros_like(train_mask); local_train[institution.node_ids] = train_mask[institution.node_ids]
        local_sparse = apply_illicit_scarcity(local_train, labels, fraction, seed + institution.id); local_illicit = local_train & (labels == 1)
        result[local_illicit] = False; result[local_sparse & (labels == 1)] = True
        counts.append({"institution": institution.id, "scarcity": float(fraction), "illicit_train_before": int(local_illicit.sum()), "illicit_train_after": int((local_sparse & (labels == 1)).sum()), "labelled_train_after": int((local_sparse & (labels >= 0)).sum())})
    return result, counts

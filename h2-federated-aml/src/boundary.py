"""Boundary identity simulation and label-free embedding alignment; no cryptographic claim."""
from __future__ import annotations
from dataclasses import dataclass
import torch
import torch.nn.functional as F


@dataclass(frozen=True)
class BoundaryPayload:
    node_ids: torch.Tensor
    embeddings: torch.Tensor


def export_boundary_embeddings(node_ids: torch.Tensor, embeddings: torch.Tensor) -> BoundaryPayload:
    return BoundaryPayload(node_ids.detach().cpu().long().clone(), embeddings.detach().cpu().float().clone())


def validate_no_raw_data(payload: BoundaryPayload) -> None:
    if payload.node_ids.ndim != 1 or payload.embeddings.ndim != 2 or len(payload.node_ids) != len(payload.embeddings): raise ValueError("Boundary payload must contain aligned node identifiers and 2-D learned embeddings only")


def collect_boundary_payload(model, data, institution, device) -> BoundaryPayload:
    model.eval()
    with torch.no_grad(): embeddings = model.encode(data.x[institution.node_ids].to(device), institution.edge_index.to(device))
    payload = export_boundary_embeddings(institution.boundary_ids, embeddings[institution.global_to_local[institution.boundary_ids]])
    validate_no_raw_data(payload); return payload


def payload_lookup(payloads: dict[int, BoundaryPayload]) -> dict[int, torch.Tensor]:
    return {int(node_id): embedding for payload in payloads.values() for node_id, embedding in zip(payload.node_ids.tolist(), payload.embeddings)}


def boundary_alignment_loss(embeddings: torch.Tensor, institution, foreign: dict[int, torch.Tensor], device) -> torch.Tensor:
    """Mean 1-cosine local/foreign boundary representation loss; foreign labels are absent."""
    losses = []
    for own_id, peers in institution.peer_pairs.items():
        local_index = institution.global_to_local[own_id]
        for peer_id in peers.tolist():
            if (foreign_embedding := foreign.get(peer_id)) is not None:
                losses.append(1 - F.cosine_similarity(embeddings[local_index].unsqueeze(0), foreign_embedding.to(device).unsqueeze(0)).mean())
    return torch.stack(losses).mean() if losses else embeddings.sum() * 0

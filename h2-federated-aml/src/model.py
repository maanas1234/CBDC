"""Centralized two-layer GCN and efficient local induced-subgraph training."""
from __future__ import annotations
import torch
import torch.nn.functional as F
from torch_geometric.nn import GCNConv
from boundary import boundary_alignment_loss, collect_boundary_payload


class GCN(torch.nn.Module):
    def __init__(self, num_features: int, hidden_dim: int = 64, cached: bool = False):
        super().__init__()
        self.conv1 = GCNConv(num_features, hidden_dim, cached=cached)
        self.conv2 = GCNConv(hidden_dim, 2, cached=cached)

    def encode(self, x, edge_index):
        return F.relu(self.conv1(x, edge_index))

    def forward(self, x, edge_index):
        return self.conv2(self.encode(x, edge_index), edge_index)


def _local_model(global_model, device):
    """Create a fresh local GCN with graph-normalization caching enabled.

    The centralized model keeps the original non-cached behavior; local induced
    graphs are fixed for the whole local update, so caching their normalization
    removes repeated graph preprocessing without changing the learned objective.
    """
    model = GCN(global_model.conv1.in_channels, global_model.conv1.out_channels, cached=True).to(device)
    model.load_state_dict(global_model.state_dict())
    return model


def train_local_selected(global_model, data, institution, train_mask, val_mask, device, epochs, lr, weight_decay):
    """Train one institution alone and keep the epoch with the best F1 on its own validation nodes."""
    from sklearn.metrics import f1_score
    model = _local_model(global_model, device)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=weight_decay)
    ids = institution.node_ids
    x, y, edge = data.x[ids].to(device), data.y[ids].to(device), institution.edge_index.to(device)
    local_train, local_val = train_mask[ids].to(device), val_mask[ids].to(device)
    best_state, best_f1 = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}, -1.0
    if not int(local_train.sum()):
        return best_state
    has_positive_val = bool((y[local_val] == 1).any())
    for _ in range(epochs):
        model.train(); optimizer.zero_grad(set_to_none=True)
        F.cross_entropy(model(x, edge)[local_train], y[local_train]).backward(); optimizer.step()
        if not has_positive_val:
            continue
        model.eval()
        with torch.no_grad(): prediction = model(x, edge)[local_val].argmax(1).cpu().numpy()
        score = f1_score(y[local_val].cpu().numpy(), prediction, zero_division=0)
        if score > best_f1:
            best_f1, best_state = score, {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
    return best_state if has_positive_val else {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}


def train_local(global_model, data, institution, train_mask, device, epochs, lr, weight_decay, foreign_embeddings=None, alignment_lambda=0.):
    model = _local_model(global_model, device)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=weight_decay)
    ids = institution.node_ids
    x = data.x[ids].to(device)
    y = data.y[ids].to(device)
    edge = institution.edge_index.to(device)
    local_train = train_mask[ids].to(device)
    if not int(local_train.sum()):
        return {k: v.detach().cpu() for k, v in model.state_dict().items()}, 0, collect_boundary_payload(model, data, institution, device)
    for _ in range(epochs):
        model.train()
        optimizer.zero_grad(set_to_none=True)
        embeddings = model.encode(x, edge)
        logits = model.conv2(embeddings, edge)
        loss = F.cross_entropy(logits[local_train], y[local_train])
        if alignment_lambda and foreign_embeddings:
            loss = loss + alignment_lambda * boundary_alignment_loss(embeddings, institution, foreign_embeddings, device)
        loss.backward()
        optimizer.step()
    return {k: v.detach().cpu() for k, v in model.state_dict().items()}, int(local_train.sum()), collect_boundary_payload(model, data, institution, device)

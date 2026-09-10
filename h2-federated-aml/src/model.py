"""Centralized two-layer GCN and local induced-subgraph optimization."""
from __future__ import annotations
import copy
import torch
import torch.nn.functional as F
from torch_geometric.nn import GCNConv
from boundary import boundary_alignment_loss, collect_boundary_payload


class GCN(torch.nn.Module):
    def __init__(self, num_features: int, hidden_dim: int = 64):
        super().__init__(); self.conv1 = GCNConv(num_features, hidden_dim); self.conv2 = GCNConv(hidden_dim, 2)

    def encode(self, x, edge_index): return F.relu(self.conv1(x, edge_index))
    def forward(self, x, edge_index): return self.conv2(self.encode(x, edge_index), edge_index)


def train_local(global_model, data, institution, train_mask, device, epochs, lr, weight_decay, foreign_embeddings=None, alignment_lambda=0.):
    model = copy.deepcopy(global_model).to(device); optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=weight_decay)
    ids = institution.node_ids; x, y, edge = data.x[ids].to(device), data.y[ids].to(device), institution.edge_index.to(device); local_train = train_mask[ids].to(device)
    if not int(local_train.sum()): return {k: v.detach().cpu() for k, v in model.state_dict().items()}, 0, collect_boundary_payload(model, data, institution, device)
    for _ in range(epochs):
        model.train(); optimizer.zero_grad(); embeddings = model.encode(x, edge); logits = model.conv2(embeddings, edge)
        loss = F.cross_entropy(logits[local_train], y[local_train])
        if alignment_lambda and foreign_embeddings: loss = loss + alignment_lambda * boundary_alignment_loss(embeddings, institution, foreign_embeddings, device)
        loss.backward(); optimizer.step()
    return {k: v.detach().cpu() for k, v in model.state_dict().items()}, int(local_train.sum()), collect_boundary_payload(model, data, institution, device)

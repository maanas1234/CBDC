"""Institution partitioning, weighted FedAvg, and local/federated AML training."""
from __future__ import annotations
from collections import OrderedDict
from dataclasses import dataclass
import torch
from torch_geometric.data import Data
from boundary import payload_lookup
from data import device_from_config, set_seed
from evaluate import evaluate_logits
from model import GCN, train_local
from scarcity import apply_institutional_illicit_scarcity


@dataclass
class Institution:
    id: int; node_ids: torch.Tensor; edge_index: torch.Tensor; global_to_local: torch.Tensor
    boundary_ids: torch.Tensor; peer_pairs: dict[int, torch.Tensor]; stats: dict


def partition_nodes(data: Data, k: int, method: str = "graph_aware", seed: int = 42) -> torch.Tensor:
    if k not in (2, 3, 5): raise ValueError("This study supports K in {2, 3, 5}")
    generator = torch.Generator().manual_seed(seed); n = data.num_nodes
    if method == "random": return torch.randperm(n, generator=generator).remainder(k)
    if method != "graph_aware": raise ValueError("method must be graph_aware or random")
    owners = torch.randperm(n, generator=generator).remainder(k); src, dst = data.edge_index.cpu(); anchors = torch.arange(k)
    for _ in range(4):
        votes = torch.zeros((n, k), dtype=torch.int32); votes.index_put_((dst, owners[src]), torch.ones(len(src), dtype=torch.int32), accumulate=True)
        owners = torch.where(votes.max(1).values > 0, votes.argmax(1), owners); owners[anchors] = torch.arange(k)
    return owners


def build_institutions(data: Data, owners: torch.Tensor) -> list[Institution]:
    src, dst = data.edge_index.cpu(); k = int(owners.max()) + 1; institutions = []; cross = owners[src] != owners[dst]
    for party in range(k):
        nodes = torch.where(owners == party)[0]; lookup = torch.full((data.num_nodes,), -1, dtype=torch.long); lookup[nodes] = torch.arange(len(nodes))
        internal = (owners[src] == party) & (owners[dst] == party); local_edges = torch.stack((lookup[src[internal]], lookup[dst[internal]]))
        outgoing, incoming = cross & (owners[src] == party), cross & (owners[dst] == party)
        own, foreign = torch.cat((src[outgoing], dst[incoming])), torch.cat((dst[outgoing], src[incoming]))
        pairs = {int(node): [] for node in torch.unique(own)}
        for node, peer in zip(own.tolist(), foreign.tolist()): pairs[node].append(peer)
        peer_pairs = {node: torch.tensor(peers, dtype=torch.long) for node, peers in pairs.items()}; labels = data.y[nodes]; internal_edges = int(internal.sum())
        stats = {"institution": party, "nodes": len(nodes), "labelled_nodes": int((labels >= 0).sum()), "illicit_nodes": int((labels == 1).sum()), "licit_nodes": int((labels == 0).sum()), "boundary_nodes": len(peer_pairs), "cross_institution_edges": int(outgoing.sum() + incoming.sum()), "internal_edges": internal_edges, "mean_internal_out_degree": internal_edges / max(len(nodes), 1)}
        institutions.append(Institution(party, nodes, local_edges, lookup, torch.tensor(list(peer_pairs), dtype=torch.long), peer_pairs, stats))
    return institutions


def fedavg(states: list[dict], weights: list[int]) -> OrderedDict:
    if not states or len(states) != len(weights) or sum(weights) <= 0: raise ValueError("states and positive weights must be aligned")
    total = float(sum(weights)); result = OrderedDict()
    for key in states[0]:
        result[key] = states[0][key].clone() if not torch.is_floating_point(states[0][key]) else sum(state[key].detach().cpu() * (weight / total) for state, weight in zip(states, weights))
    return result


def _institutions_and_training(data, splits, k, partition_method, scarcity, seed):
    institutions = build_institutions(data, partition_nodes(data, k, partition_method, seed))
    return institutions, *apply_institutional_illicit_scarcity(splits["train"], data.y, institutions, scarcity, seed)


def run_federated(data, splits, *, k=3, partition_method="graph_aware", seed=42, rounds=10, local_epochs=1, lr=.01, hidden_dim=64, device="auto", scarcity=1., boundary_lambda=0.):
    """Run weighted FedAvg, optionally adding label-free boundary alignment locally."""
    set_seed(seed); dev = device_from_config(device); institutions, train_mask, scarcity_counts = _institutions_and_training(data, splits, k, partition_method, scarcity, seed)
    model = GCN(data.num_node_features, hidden_dim).to(dev); foreign_embeddings = {}
    for round_number in range(rounds):
        updates = [train_local(model, data, institution, train_mask, dev, local_epochs, lr, 5e-4, foreign_embeddings, boundary_lambda) for institution in institutions]
        model.load_state_dict(fedavg([update[0] for update in updates], [update[1] for update in updates]))
        foreign_embeddings = {} if boundary_lambda == 0 else payload_lookup({institution.id: update[2] for institution, update in zip(institutions, updates)})
        print(f"Round {round_number + 1}/{rounds}: aggregated {sum(update[1] for update in updates)} labelled local samples")
    model.eval()
    with torch.no_grad(): logits = model(data.x.to(dev), data.edge_index.to(dev)).cpu()
    return evaluate_logits(logits, data.y, splits["test"]), institutions, model.cpu(), train_mask, scarcity_counts


def run_local_only(data, splits, *, k=3, partition_method="graph_aware", seed=42, epochs=10, lr=.01, hidden_dim=64, device="auto", scarcity=1.):
    set_seed(seed); dev = device_from_config(device); institutions, train_mask, scarcity_counts = _institutions_and_training(data, splits, k, partition_method, scarcity, seed)
    initial_model = GCN(data.num_node_features, hidden_dim).to(dev); logits = torch.zeros((data.num_nodes, 2))
    for institution in institutions:
        state, _, _ = train_local(initial_model, data, institution, train_mask, dev, epochs, lr, 5e-4)
        local_model = GCN(data.num_node_features, hidden_dim).to(dev); local_model.load_state_dict(state); local_model.eval()
        with torch.no_grad(): logits[institution.node_ids] = local_model(data.x[institution.node_ids].to(dev), institution.edge_index.to(dev)).cpu()
    return evaluate_logits(logits, data.y, splits["test"]), institutions, train_mask, scarcity_counts

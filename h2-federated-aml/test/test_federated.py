import torch
from torch_geometric.data import Data
from federated import build_institutions, fedavg, partition_nodes
from model import GCN, train_local
from scarcity import apply_institutional_illicit_scarcity
def graph(): return Data(x=torch.randn(6, 2), y=torch.tensor([0, 1, -1, 0, 1, -1]), edge_index=torch.tensor([[0, 1, 2, 3, 4], [1, 2, 3, 4, 5]]), num_nodes=6)
def test_weighted_fedavg(): assert torch.allclose(fedavg([{"w": torch.tensor([1.])}, {"w": torch.tensor([4.])}], [1, 3])["w"], torch.tensor([3.25]))
def test_partitions_and_boundaries_cover_every_node():
    data = graph(); institutions = build_institutions(data, partition_nodes(data, 2, "random", 1))
    assert sum(len(institution.node_ids) for institution in institutions) == data.num_nodes
def test_per_institution_scarcity_counts_and_keeps_licit_labels():
    data = graph(); institutions = build_institutions(data, torch.tensor([0, 0, 0, 1, 1, 1])); train = torch.tensor([1, 1, 0, 1, 1, 0], dtype=torch.bool)
    sparse, counts = apply_institutional_illicit_scarcity(train, data.y, institutions, .5, 5)
    assert len(counts) == 2 and all(row["illicit_train_after"] <= row["illicit_train_before"] for row in counts)
    assert torch.equal(sparse[data.y == 0], train[data.y == 0]) and not sparse[2] and not sparse[5]
def test_local_training_returns_cpu_state_and_payload():
    data = graph(); institutions = build_institutions(data, torch.tensor([0, 0, 0, 1, 1, 1])); train = torch.tensor([1, 1, 0, 1, 1, 0], dtype=torch.bool)
    state, samples, payload = train_local(GCN(2, 4), data, institutions[0], train, torch.device("cpu"), 1, .01, 0.)
    assert samples == 2 and all(value.device.type == "cpu" for value in state.values()) and payload.embeddings.shape[1] == 4

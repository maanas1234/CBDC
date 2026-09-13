import torch
from torch_geometric.data import Data
from boundary import boundary_alignment_loss, collect_boundary_payload, export_boundary_embeddings, payload_lookup, validate_no_raw_data
from federated import build_institutions
from model import GCN
def graph(): return Data(x=torch.randn(4, 3), y=torch.tensor([0, 1, -1, 0]), edge_index=torch.tensor([[0, 1, 2], [1, 2, 3]]), num_nodes=4)
def test_payload_shape_validation_and_embedding_dimension():
    validate_no_raw_data(export_boundary_embeddings(torch.tensor([4, 5]), torch.randn(2, 8)))
    data = graph(); institutions = build_institutions(data, torch.tensor([0, 0, 1, 1])); payload = collect_boundary_payload(GCN(3, 5), data, institutions[0], torch.device("cpu"))
    assert payload.embeddings.shape[1] == 5 and len(payload.node_ids) == len(payload.embeddings)
def test_boundary_identity_pairs_match_foreign_owner_and_payload_lookup():
    data = graph(); owners = torch.tensor([0, 0, 1, 1]); institutions = build_institutions(data, owners)
    for institution in institutions:
        for own_id, peer_ids in institution.peer_pairs.items():
            assert owners[own_id] == institution.id and all(owners[peer] != institution.id for peer in peer_ids.tolist())
    assert torch.equal(payload_lookup({0: export_boundary_embeddings(torch.tensor([7]), torch.tensor([[1., 2.]]))})[7], torch.tensor([1., 2.]))
def test_alignment_is_cosine_and_receives_no_labels():
    class Institution: peer_pairs = {1: torch.tensor([9])}; global_to_local = torch.tensor([-1, 0])
    assert torch.isclose(boundary_alignment_loss(torch.tensor([[1., 0.]]), Institution(), {9: torch.tensor([1., 0.])}, torch.device("cpu")), torch.tensor(0.))

import pandas as pd
import torch
from boundary import BoundaryPayload
from eval_stats import paired_significance, summarize_results
from privacy import privatize_boundary_payload, privatize_model_update


def test_update_clipping_bounds_institution_delta_without_noise():
    base = {"w": torch.tensor([0.0, 0.0])}
    local = {"w": torch.tensor([3.0, 4.0])}
    protected = privatize_model_update(base, local, 1.0, 0.0)
    assert torch.allclose(torch.linalg.vector_norm(protected["w"] - base["w"]), torch.tensor(1.0))


def test_boundary_embedding_privacy_preserves_visible_ids_and_bounds_vectors():
    payload = BoundaryPayload(torch.tensor([7]), torch.tensor([[3.0, 4.0]]))
    protected = privatize_boundary_payload(payload, 1.0, 0.0)
    assert torch.equal(protected.node_ids, payload.node_ids)
    assert torch.allclose(torch.linalg.vector_norm(protected.embeddings, dim=1), torch.tensor([1.0]))


def test_seed_summary_and_paired_significance_use_measured_matched_rows():
    rows = []
    for seed, local, fed, boundary in ((11, .4, .5, .6), (12, .5, .6, .7), (13, .6, .7, .8)):
        for method, f1 in (("local_only", local), ("fedavg", fed), ("fedavg_boundary", boundary)):
            rows.append({"experiment": "main_scarcity", "method": method, "scarcity": .1, "institutions": 3, "seed": seed, "f1": f1, "pr_auc": f1 + .1})
    frame = pd.DataFrame(rows)
    summary = summarize_results(frame)
    local_summary = summary[summary.method == "local_only"].iloc[0]
    assert local_summary.f1_mean == .5
    assert round(local_summary.f1_std, 6) == .1
    tests = paired_significance(frame)
    assert set(tests.comparison) == {"local_only vs fedavg", "fedavg_boundary vs fedavg"}
    assert (tests.n_paired_seeds == 3).all()
    assert (tests.p_value > 0).all() and (tests.p_value <= 1).all()
    assert set(tests.loc[tests.comparison == "local_only vs fedavg", "effect_direction"]) == {"second_higher"}
    assert set(tests.loc[tests.comparison == "fedavg_boundary vs fedavg", "effect_direction"]) == {"first_higher"}
    assert tests.statistically_significant.dtype == bool

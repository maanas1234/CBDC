import pandas as pd
import torch
from scarcity import apply_illicit_scarcity
from data import build_transaction_index, convert_class_labels, make_splits, map_edge_ids

def test_transaction_mapping_is_contiguous_and_rejects_duplicates():
    assert build_transaction_index([30, 10, 20]) == {30: 0, 10: 1, 20: 2}
    try: build_transaction_index([1, 1])
    except ValueError: pass
    else: assert False
def test_edge_mapping_drops_only_missing_endpoints():
    mapped = map_edge_ids(pd.DataFrame({"txId1": [10, 20], "txId2": [20, 99]}), {10: 0, 20: 1})
    assert mapped[["source_idx", "target_idx"]].values.tolist() == [[0, 1]]
def test_label_conversion_preserves_unknown_as_minus_one():
    labels = convert_class_labels(pd.DataFrame({"txId": [10, 20, 99], "class": ["1", "2", "unknown"]}), {10: 0, 20: 1, 30: 2})
    assert labels.tolist() == [1, 0, -1]
def test_splits_exclude_unknown_and_are_reproducible():
    y = torch.tensor(([1, 0] * 15) + [-1]); first = make_splits(y, 3); second = make_splits(y, 3)
    assert all(torch.equal(first[key], second[key]) for key in first) and not any(mask[-1] for mask in first.values())
def test_scarcity_removes_only_illicit_training_labels():
    y = torch.tensor([1, 1, 1, 1, 0, 0, -1]); train = torch.tensor([1, 1, 1, 1, 1, 1, 0], dtype=torch.bool); sparse = apply_illicit_scarcity(train, y, .5, 7)
    assert int((sparse & (y == 1)).sum()) == 2 and torch.equal(sparse[y == 0], train[y == 0]) and not sparse[-1]

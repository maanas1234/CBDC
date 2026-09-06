"""
Splits the trained FraudClassifier into two halves for H1's partial-proving
mechanism:

  EARLY  (165 -> 32, Linear+BatchNorm+ReLU+Dropout): the expensive part.
          Run off-chain, NOT proven on every inference. Its output is
          committed to via a Poseidon hash (see proofs/prove_partial.py)
          so it can't be silently changed later without the hash changing.

  LATE   (32 -> 16 -> 1, Linear+BatchNorm+ReLU+Linear): the cheap
          "decision" part. THIS is what actually gets a ZK proof — proving
          "given this committed intermediate activation, the model's
          final layers produce this exact output." This is the "disputed
          part" that gets proven when someone challenges a flagged
          transaction.

This is an exact split of the same computation (not an approximation),
so it does not change model accuracy at all vs the full model — the
whole benefit here is proving cost, not any accuracy tradeoff.

NOTE ON LAYER INDICES: FraudClassifier's net is now
  [0] Linear(n->h1)  [1] BatchNorm(h1)  [2] ReLU  [3] Dropout
  [4] Linear(h1->h2) [5] BatchNorm(h2)  [6] ReLU  [7] Linear(h2->1)
If you change the architecture in train_baseline.py again, update the
slice indices below to match — this split assumes exactly these 8 layers
in this order.

Run: python3 split_model.py
Requires: baseline_model.pt (from train_baseline.py)
Outputs: early_model.onnx, late_model.onnx
"""

import torch
import torch.nn as nn

from train_baseline import FraudClassifier, N_FEATURES


class EarlyHalf(nn.Module):
    """165 -> 32, Linear + BatchNorm + ReLU + Dropout. The expensive
    layer — NOT proven per-inference. Dropout is a no-op in eval mode,
    kept here only so indices line up cleanly with the full net."""

    def __init__(self, full_net):
        super().__init__()
        self.layers = nn.Sequential(full_net[0], full_net[1], full_net[2], full_net[3])

    def forward(self, x):
        return self.layers(x)


class LateHalf(nn.Module):
    """32 -> 16 -> 1, Linear + BatchNorm + ReLU + Linear. The proven part."""

    def __init__(self, full_net):
        super().__init__()
        self.layers = nn.Sequential(full_net[4], full_net[5], full_net[6], full_net[7])

    def forward(self, x):
        return self.layers(x)


def split_and_export():
    # infer hidden1/hidden2 from the saved checkpoint itself, rather than
    # assuming a fixed size — avoids exactly the mismatch you'd get if
    # train_baseline.py was last run with different --hidden1/--hidden2
    # values than whatever this script assumes.
    state_dict = torch.load("baseline_model.pt")
    hidden1 = state_dict["net.0.weight"].shape[0]
    hidden2 = state_dict["net.4.weight"].shape[0]
    print(f"Detected architecture from checkpoint: 165 -> {hidden1} -> {hidden2} -> 1")

    full_model = FraudClassifier(hidden1=hidden1, hidden2=hidden2)
    full_model.load_state_dict(state_dict)
    full_model.eval()

    early = EarlyHalf(full_model.net)
    late = LateHalf(full_model.net)
    early.eval()
    late.eval()

    # sanity check: early(x) -> late(...) must exactly equal full_model(x)
    torch.manual_seed(0)
    test_x = torch.randn(5, N_FEATURES)
    with torch.no_grad():
        full_out = full_model(test_x)
        split_out = late(early(test_x))
    max_diff = (full_out - split_out).abs().max().item()
    assert max_diff < 1e-5, f"Split doesn't match full model! max diff = {max_diff}"
    print(f"Split verified exact: max diff vs full model = {max_diff:.2e}")

    dummy_early_in = torch.randn(1, N_FEATURES)
    torch.onnx.export(
        early, dummy_early_in, "early_model.onnx",
        input_names=["input"], output_names=["intermediate"],
        opset_version=11, dynamo=False,
    )

    dummy_late_in = torch.randn(1, hidden1)
    torch.onnx.export(
        late, dummy_late_in, "late_model.onnx",
        input_names=["intermediate"], output_names=["output"],
        opset_version=11, dynamo=False,
    )

    print(f"Saved early_model.onnx (165->{hidden1}, NOT proven per-inference)")
    print(f"Saved late_model.onnx ({hidden1}->{hidden2}->1, THIS gets proven on dispute)")


if __name__ == "__main__":
    split_and_export()

"""Single command-line entry point for data preparation and H2 workflows."""
from __future__ import annotations
import argparse
import pandas as pd
import torch
import torch.nn.functional as F
from data import RESULTS_DIR, device_from_config, inspect_data, load_graph, make_splits, prepare_data, set_seed
from evaluate import evaluate_logits
from experiments import run_config
from federated import run_federated
from model import GCN


def run_centralized(epochs=100, seed=42, device="auto"):
    set_seed(seed); dev = device_from_config(device); data = load_graph().to(dev); splits = {name: mask.to(dev) for name, mask in make_splits(data.y.cpu(), seed).items()}
    model = GCN(data.num_node_features).to(dev); optimizer = torch.optim.Adam(model.parameters(), lr=.01, weight_decay=5e-4); best_state, best_f1 = None, -1
    for _ in range(epochs):
        model.train(); optimizer.zero_grad(); logits = model(data.x, data.edge_index); loss = F.cross_entropy(logits[splits["train"]], data.y[splits["train"]]); loss.backward(); optimizer.step()
        model.eval()
        with torch.no_grad(): validation = evaluate_logits(model(data.x, data.edge_index), data.y, splits["val"])
        if validation["f1"] > best_f1: best_f1, best_state = validation["f1"], {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
    model.load_state_dict(best_state); model.eval()
    with torch.no_grad(): metrics = evaluate_logits(model(data.x, data.edge_index), data.y, splits["test"])
    RESULTS_DIR.mkdir(exist_ok=True); torch.save({"state_dict": model.state_dict(), "seed": seed}, RESULTS_DIR / "centralized_gcn.pt"); pd.DataFrame([{**metrics, "method": "centralized_gcn", "seed": seed, "epochs": epochs}]).to_csv(RESULTS_DIR / "baseline_results.csv", index=False)
    print("FINAL CENTRALIZED BASELINE", metrics); return metrics


def main() -> None:
    parser = argparse.ArgumentParser(); commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("inspect-data"); commands.add_parser("prepare-data")
    centralized = commands.add_parser("centralized"); centralized.add_argument("--epochs", type=int, default=100); centralized.add_argument("--seed", type=int, default=42); centralized.add_argument("--device", default="auto")
    federated = commands.add_parser("federated"); federated.add_argument("--institutions", type=int, default=3, choices=[2, 3, 5]); federated.add_argument("--rounds", type=int, default=10); federated.add_argument("--local-epochs", type=int, default=1); federated.add_argument("--partition", default="graph_aware", choices=["graph_aware", "random"]); federated.add_argument("--seed", type=int, default=42)
    full = commands.add_parser("full-experiment"); full.add_argument("--config", default=str(RESULTS_DIR.parent / "experiments" / "configs" / "default.yaml"))
    args = parser.parse_args()
    if args.command == "inspect-data": inspect_data()
    elif args.command == "prepare-data": prepare_data()
    elif args.command == "centralized": run_centralized(args.epochs, args.seed, args.device)
    elif args.command == "federated":
        data = load_graph(); metrics, institutions, model, _, counts = run_federated(data, make_splits(data.y, args.seed), k=args.institutions, partition_method=args.partition, seed=args.seed, rounds=args.rounds, local_epochs=args.local_epochs)
        RESULTS_DIR.mkdir(exist_ok=True); pd.DataFrame([{**metrics, "method": "fedavg", "institutions": args.institutions, "partition": args.partition, "scarcity": 1.0}]).to_csv(RESULTS_DIR / "federated_results.csv", index=False); pd.DataFrame([institution.stats for institution in institutions]).to_csv(RESULTS_DIR / "institution_stats.csv", index=False); pd.DataFrame(counts).to_csv(RESULTS_DIR / "per_institution_scarcity_counts.csv", index=False); torch.save(model.state_dict(), RESULTS_DIR / "fedavg_gcn.pt"); print(metrics)
    else: run_config(args.config)


if __name__ == "__main__": main()

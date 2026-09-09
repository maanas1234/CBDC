# H2: Federated AML Detection Under Label Scarcity

This reproducible research prototype tests—not assumes—the proposition that per-institution scarcity of labelled illicit examples harms federated AML detection and that cross-institution boundary embeddings can mitigate that harm without sharing raw graphs or raw features.

It follows the progression from centralized Elliptic1 GCN AML (Weber et al., 2019), through structural graph context (Bellei et al., 2024), to the cross-institution setting represented by FedGraph-VASP. The gap tested here is scarce local illicit supervision in a federated graph setting.

## Data and labels

The project uses the supplied Elliptic1 files. Transaction IDs are mapped once to contiguous node indices. Labels are `1` illicit, `0` licit and `-1` unknown. Unknown nodes are **never** cast as licit labels, included in supervised loss, or included in evaluation. The raw dataset is excluded from Git.

## Local environment

Use the existing project environment already configured in the local VS Code terminal. This repository does not require an environment rebuild to run the experiments below.

## Run order

Run commands from the project root:

```powershell
python src/main.py inspect-data
python src/main.py prepare-data
python src/main.py centralized
python src/main.py federated --institutions 3 --partition graph_aware
pytest -q tests
python src/main.py full-experiment --config experiments/configs/default.yaml
```

`python src/main.py full-experiment --config experiments/configs/default.yaml` is the complete H2 command. It runs the K=3 Local-only/FedAvg/FedAvg+Boundary scarcity comparison; the six-value lambda ablation at fixed 10% scarcity; and the K=2/3/5 method comparison at fixed 10% scarcity. It writes only measured rows: `scarcity_results.csv`, `boundary_results.csv`, `federated_results.csv`, `lambda_ablation_results.csv`, `institution_count_ablation_results.csv`, `ablation_results.csv`, `per_institution_scarcity_counts.csv`, `institution_stats.csv`, and six figures.

## Experimental design

The labelled nodes have one deterministic stratified 70/15/15 train/validation/test split. That split and all test labels remain fixed across methods and scarcity levels. Scarcity applies only to illicit *training* labels at 100%, 50%, 20%, 10%, 5%, and 1%; licit training labels and all validation/test labels are unchanged. Metrics are accuracy, precision, recall, F1, PR-AUC, ROC-AUC, and a confusion matrix. F1 and PR-AUC should be primary given the imbalance.

Elliptic1 has no real VASP ownership. Institutions are therefore explicitly **simulated**, not claimed to be real. The default graph-aware partition uses deterministic neighbour-vote propagation; `random` is a baseline. K=2, 3, and 5 are supported. Per-institution node, label, illicit, licit, boundary, and cross-edge statistics are saved.

Local GCNs train on each institution's induced graph. FedAvg aggregates only model parameters, weighted by local supervised sample count. The centralized architecture remains the supplied two-layer GCN (default hidden size 64).

## Boundary signal and identity simulation

A boundary node is an endpoint of a cross-institution edge. For each such edge, the simulation records the pair of globally unique, contiguous node indices `(local endpoint, foreign endpoint)`. This is the explicit assumed shared identity channel; two copied nodes are not silently treated as naturally identifiable. These IDs are a simulation-specific matching token, not an assertion that real VASPs can exchange raw transaction identifiers.

After local training, an institution exports only `{boundary node ID, learned embedding}`. For an outgoing boundary edge, the receiving party matches the foreign endpoint ID and applies `1 - cosine_similarity(h_local, h_foreign)`. The foreign embedding is detached and no foreign illicit/licit label is in this objective. The mechanism is therefore a **label-free cross-institution signal**, embedded in an otherwise weakly supervised system because each local classifier uses its own labels.

In a real VASP deployment, an agreed privacy-preserving counterparty/transfer identifier and authenticated exchange would be required; raw on-chain graph access and simulated global IDs cannot be assumed.

## Privacy scope and limitations

`boundary.py` validates the research payload shape and prevents this code path from carrying raw features or neighbourhoods. The simulation shares model updates and learned boundary embeddings only. It does **not** implement secure aggregation, encryption, differential privacy, a privacy proof, or production authentication. Embeddings can leak information and should not be described as formally private.

## Interpreting H2

For every measured scarcity level, compare local-only, FedAvg, and FedAvg + boundary alignment. Degradation is `metric(100%) - metric(level)`; positive mitigation is `degradation(FedAvg) - degradation(boundary)`. Run multiple seeds and report variation before drawing an inference. A positive mitigation alone is not proof: the result may support, partially support, fail to support, or falsify H2 under the tested conditions. Do not change the evaluation set or tune against a desired conclusion.

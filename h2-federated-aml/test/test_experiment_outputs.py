import pandas as pd
import yaml
from pathlib import Path
from experiments import write_outputs
def test_default_config_declares_full_h2_matrix():
    config_path = Path(__file__).resolve().parents[1] / "experiments" / "configs" / "default.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert config["scarcity_levels"] == [1.0, .5, .2, .1, .05, .01]
    assert config["lambda_values"] == [0.0, .01, .05, .1, .5, 1.0] and config["institution_counts"] == [2, 3, 5]
def test_result_writer_creates_machine_readable_tables_and_figures(tmp_path):
    rows = [{"experiment":"main_scarcity", "method":method, "scarcity":scarcity, "seed":1, "institutions":3, "lambda":.05 if method == "fedavg_boundary" else 0., "f1":.5, "pr_auc":.6, "accuracy":.7, "precision":.4, "recall":.8, "roc_auc":.75, "confusion_matrix":"[[1,0],[0,1]]"} for method in ("local_only", "fedavg", "fedavg_boundary") for scarcity in (1.0, .1)]
    stats = [{"institution":0, "institutions":3, "illicit_nodes":2, "licit_nodes":5, "boundary_nodes":3, "cross_institution_edges":4}, {"institution":1, "institutions":3, "illicit_nodes":3, "licit_nodes":4, "boundary_nodes":2, "cross_institution_edges":4}]
    counts = [{"institution":0, "scarcity":.1, "illicit_train_before":10, "illicit_train_after":1, "labelled_train_after":20, "method":"local_only", "seed":1, "institutions":3, "experiment":"main_scarcity"}]
    write_outputs(pd.DataFrame(rows), pd.DataFrame(), pd.DataFrame(), counts, stats, tmp_path)
    assert (tmp_path / "scarcity_results.csv").exists() and (tmp_path / "lambda_ablation_results.csv").exists() and (tmp_path / "figures" / "performance_vs_label_scarcity.png").exists()

"""Labelled-node AML evaluation metrics and result output helpers."""
from __future__ import annotations
import numpy as np
import torch
from sklearn.metrics import accuracy_score, average_precision_score, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score


def evaluate_logits(logits: torch.Tensor, labels: torch.Tensor, mask: torch.Tensor) -> dict:
    if int(mask.sum()) == 0: raise ValueError("Cannot evaluate an empty mask")
    y = labels[mask].detach().cpu().numpy()
    if np.any(y < 0): raise ValueError("Evaluation mask contains unknown labels")
    scores = torch.softmax(logits[mask], dim=1)[:, 1].detach().cpu().numpy(); prediction = (scores >= .5).astype(int)
    metrics = {"accuracy": accuracy_score(y, prediction), "precision": precision_score(y, prediction, zero_division=0), "recall": recall_score(y, prediction, zero_division=0), "f1": f1_score(y, prediction, zero_division=0), "pr_auc": average_precision_score(y, scores), "confusion_matrix": confusion_matrix(y, prediction, labels=[0, 1]).tolist()}
    metrics["roc_auc"] = roc_auc_score(y, scores) if len(np.unique(y)) == 2 else float("nan")
    return metrics

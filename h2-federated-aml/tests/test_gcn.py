import torch
from model import GCN
from evaluate import evaluate_logits
def test_gcn_forward_and_metrics():
 model=GCN(3,8); x=torch.randn(4,3); edge=torch.tensor([[0,1,2],[1,2,3]]); logits=model(x,edge)
 assert logits.shape == (4,2)
 assert {'f1','pr_auc','roc_auc','confusion_matrix'} <= evaluate_logits(logits,torch.tensor([0,1,0,1]),torch.ones(4,dtype=torch.bool)).keys()

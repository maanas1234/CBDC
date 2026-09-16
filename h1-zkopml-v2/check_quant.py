import numpy as np, pickle, json, subprocess, ezkl, os
from onnx_builder import build
from quant import quantize_units, trace, S
from data import load, temporal_split, apply_scaler
m = pickle.load(open("models/W32_B1.pkl","rb"))
X,y,ts = load(); _,_,(Xte,yte),_ = temporal_split(X,y,ts)
Xte = apply_scaler(Xte, m["scaler"])
qu = quantize_units(m["units"])
os.makedirs("/tmp/cq", exist_ok=True)
build(m["units"], "/tmp/cq/mono.onnx")
ok = 0
for i in [0, 5, 17]:
    x = Xte[i]
    acts = trace(qu, x[None])
    np.save("/tmp/cq/x.npy", x)
    r = subprocess.run(["python3","prover.py","/tmp/cq/mono.onnx","/tmp/cq/x.npy",f"/tmp/cq/w{i}","public","public","1"],capture_output=True,text=True)
    w = json.load(open(f"/tmp/cq/w{i}/witness.json"))
    ez = ezkl.felt_to_int(w["outputs"][0][0])
    print(i, "ezkl out int", ez, "emu", int(acts[-1][0,0]), "match", ez == int(acts[-1][0,0]))

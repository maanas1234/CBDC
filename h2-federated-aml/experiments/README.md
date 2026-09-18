# Experiments

`configs/default.yaml` holds the controlled H2 matrix. It runs all six scarcity levels for K=3, the lambda set `0, .01, .05, .1, .5, 1.0` at 10% scarcity, and K=2/3/5 at 10% scarcity. The default is intentionally modest (one seed, ten global rounds); increase `seeds` and rounds for a report with uncertainty estimates. Results are only written after a run completes.

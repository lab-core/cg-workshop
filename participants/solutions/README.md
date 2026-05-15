# Reference solutions

**Spoiler — peek at this folder only after you have given each exercise a
serious attempt!**

`solutions/vrp/` mirrors `participants/vrp/` and contains a fully working
implementation of every TODO hole. The `vrp/` package layout is identical,
so you can run the solution version of any check by inserting
`solutions/` into the Python path:

```bash
cd participants/
source .venv/bin/activate

PYTHONPATH=solutions python -m vrp.smoke_test
PYTHONPATH=solutions python -m vrp.tests.exA_master
PYTHONPATH=solutions python -m vrp.tests.exB_pricing --instance R101.txt --iter 0
PYTHONPATH=solutions python -m vrp.tests.exC_cg --instance R101_25.txt --K 50
PYTHONPATH=solutions python -m vrp.tests.exD_diving --instance R101_25.txt
PYTHONPATH=solutions python -m vrp.tests.exE_bnp --instance R101_25.txt
```

The reference master problem includes the vehicle-count constraint
$\sum_p x_p \le K$ so the Lagrangian bound (Trick 7) is mathematically
valid:

$$\text{LB} = \sum_{i\in\mathcal N}\pi_i + K\sigma + K\cdot\min(0,\bar c^*),$$

where $\sigma$ is the dual on the vehicle-count constraint and
$\bar c^* = \min_p \bar c_p$ is the reduced-cost optimum from the
**exact** pricer.

---

## Comparison and visualisation scripts

Both `compare_cg` and `compare_bnp` are available in
`solutions/vrp/tests/` and in the participants' `vrp/tests/` (identical
content). Run them from the `participants/` directory with
`PYTHONPATH=solutions`:

```bash
cd participants/
source .venv/bin/activate

# CG — compare pricing batch sizes
PYTHONPATH=solutions python -m vrp.tests.compare_cg \
    --instance RC101.txt --Ks 1 5 20 50

# CG — compare Wentges smoothing
PYTHONPATH=solutions python -m vrp.tests.compare_cg \
    --instance RC101.txt --alphas 0 0.2 0.5

# B&P — compare K values
PYTHONPATH=solutions python -m vrp.tests.compare_bnp \
    --instance RC101.txt --Ks 5 20 50

# B&P — compare gap thresholds
PYTHONPATH=solutions python -m vrp.tests.compare_bnp \
    --instance RC101.txt --gaps 0 2 5

# B&P — depth-first vs best-first
PYTHONPATH=solutions python -m vrp.tests.compare_bnp \
    --instance RC101.txt --search both
```

Each figure has two rows: bounds/gap vs **nodes processed** (top) and
vs **wall-clock time** (bottom). Pass `--save <file.png>` to write the
figure to disk instead of displaying it.

### `compare_cg` flags

| Flag | Default | Effect |
|------|---------|--------|
| `--alphas A …` | `0 0.1 0.3 0.5` | compare α values; K fixed at `--K` |
| `--Ks K …` | — | compare batch sizes; α fixed at `--alpha` |
| `--K` | `50` | K used when `--alphas` is active |
| `--alpha` | `0.0` | α used when `--Ks` is active |

### `compare_bnp` flags

| Flag | Default | Effect |
|------|---------|--------|
| `--gaps G …` | — | compare gap stop thresholds |
| `--alphas A …` | — | compare Wentges α values |
| `--Ks K …` | — | compare pricing batch sizes |
| `--search` | — | `depth-first`, `best-first`, or `both` |
| `--K` | `50` | K used for all modes except `--Ks` |

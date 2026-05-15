# Column Generation & Branch-and-Price — Workshop Lab Kit

Polytechnique Montréal — 4-hour practical workshop.

This folder contains the code skeleton, instances, and PDFs you need to
follow the workshop. It pairs with two slide decks shipped alongside it:

- `theory.pdf` — the theoretical content (CG, RCSPP, B&P, Lagrangian bound).
- `lab.pdf`    — the lab walkthrough (this file in slide form).

You will fill in **TODO holes** marked `EX-A.k`, `EX-B.k`, … inside the
Python sources. Every hole is listed in the lab deck and in section 3 of
this README — go through them in order so nothing is skipped.

---

## 1. Setup

For Linux / macOS users, Python 3.10+ is recommended; Windows users should use WSL or a Python distribution like Anaconda. The code is tested on
Python 3.10, but should work on 3.8+.

For Linux / macOS users:
```bash
cd python/
python3 -m venv .venv
source .venv/bin/activate
```

For Windows users with PowerShell:
```bash
cd python/
python -m venv .venv
.venv\Scripts\activate
```

Then install the requirements as well as the workshop pricer (`rcspp` is on TestPyPI, with its
dependencies on regular PyPI):

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple rcspp==0.0.1.dev0
```

Run the smoke check — this exercises `highspy` + `rcspp` and **does not
depend on any code you will modify**, so it should pass before you touch
anything.

```bash
python -m vrp.smoke_test
```

Expected last line: `[smoke] OK -- environment is ready.`

To run the same checks against the reference implementation:

```bash
cd solutions/
python -m vrp.smoke_test
python -m vrp.tests.exA_master
python -m vrp.tests.exB_pricing
python -m vrp.tests.exC_cg
python -m vrp.tests.exD_diving
python -m vrp.tests.exE_bnp
```

(Each check defaults to the small `toy.txt` instance; pass
`--instance R101_25.txt` for a larger Solomon file.)

---

## 2. File map

```
python/
├── README.md                <-- you are here
├── requirements.txt
├── theory.pdf, lab.pdf
├── instances/               <-- toy.txt + a handful of Solomon files
│   └── duals/               <-- saved LP dual prices for exB_pricing
├── solutions/               <-- reference solutions (peek only after trying!)
└── vrp/
    ├── instance.py          <-- Customer / Instance — read-only
    ├── instance_reader.py   <-- Solomon parser     — read-only
    ├── smoke_test.py        <-- environment check
    ├── vrp.py               <-- main driver         ✏️ EX-A.3, B.3, C.1..C.3
    ├── cg/
    │   ├── path.py, mp_solution.py
    │   ├── master_problem.py    ✏️ EX-A.1, A.2, D.1
    │   ├── pricing.py           ✏️ EX-B.1, B.2, E.4
    │   ├── bound.py             ✏️ EX-C.4 (Lagrangian bound)
    │   ├── diving.py            ✏️ EX-D.2, D.3
    │   └── bnp.py               ✏️ EX-E.1, E.2, E.3 (loop is provided!)
    └── tests/                <-- progressive checks (NOT pytest)
        ├── exA_master.py
        ├── exB_pricing.py
        ├── exC_cg.py
        ├── exD_diving.py
        └── exE_bnp.py
```

---

## 3. Exercise plan

| Exercise | Holes to fill                  | Test                              |
|---------:|--------------------------------|-----------------------------------|
| **A**    | A.1, A.2, A.3                  | `python -m vrp.tests.exA_master`  |
| **B**    | B.1, B.2, B.3                  | `python -m vrp.tests.exB_pricing` |
| **C**    | C.2, C.3, C.4, C.5             | `python -m vrp.tests.exC_cg`      |
| **D**    | D.1, D.2, D.3                  | `python -m vrp.tests.exD_diving`  |
| **E**    | E.1, E.2, E.3, E.4             | `python -m vrp.tests.exE_bnp`     |

**A.1** — `vrp/cg/master_problem.py` — vehicle-count row $\sum_p x_p \le K$
*then* one $=1$ covering row per customer.
**A.2** — `vrp/cg/master_problem.py` — add one column per Path (no upper
bound on `x_p`, coefficient 1 on the vehicle row).
**A.3** — `vrp/vrp.py:generate_initial_paths` — one round-trip per customer.

**B.1, B.2** — `vrp/cg/pricing.py` — build the resource graph and per-arc
cost / increments.
Arc reduced cost: `distance(u,v) − π_u`, where `π_u` is the dual of the
node we *leave*.  For the depot, `π_0 = σ` (the vehicle-count dual) — **not
0** — so that every path's reduced cost includes the `−σ` vehicle term.
The CG loop sets `dual_by_id[depot_id] = sol.sigma` before calling the
pricer; use `dual_by_id.get(origin_id, 0.0)` uniformly (no depot
special-case).
**B.3** — `vrp/vrp.py:solve_subproblem` — wire the pricer.
Use `dual_by_id.setdefault(depot_id, 0.0)` as a safety net (the CG loop
already sets the depot entry to `sol.sigma`).

**C.2, C.3, C.4** — `vrp/vrp.py` CG loop: multi-column add, Wentges
smoothing (optional), per-iteration log line.
**C.5** — `vrp/cg/bound.py` — Lagrangian bound (Trick 7).
**Do not rebuild the master between CG iterations**: just
`master.add_column(...)` the new ones and `master.solve(relax=True)`
warm-starts.

**D.1** — `vrp/cg/master_problem.py:_set_integrality` — flip variable
kind between continuous and integer. **The RMH won't actually solve a
binary MIP until you implement this.**
**D.2, D.3** — `vrp/cg/diving.py` — pick the column to fix, re-run CG.

**E.1, E.2, E.3** — `vrp/cg/bnp.py` — aggregated arc flow,
most-fractional arc, build the two children. The B&P search loop itself
is **fully provided**: best-first by Lagrangian bound, dive at the
root, RMH every 10 nodes thereafter.
**E.4** — `vrp/cg/pricing.py` — skip forbidden arcs at graph build.

Each check script prints expected vs computed values then a final
`[OK]` or `[FAIL]` line. You can leave later exercises as
`NotImplementedError` while running an earlier check.

---

## 4. Working with the checks

```bash
python -m vrp.tests.exA_master --instance toy.txt
python -m vrp.tests.exB_pricing --instance R101_25.txt
python -m vrp.tests.exC_cg --instance R101_25.txt --nb-cols 50
python -m vrp.tests.exD_diving --instance R101_25.txt
python -m vrp.tests.exE_bnp --instance R101_25.txt
```

---

## 5. Comparison and visualisation tools

Two scripts let you run the same instance under different configurations
and plot convergence side-by-side. Each produces a figure with:

- **Top row** — upper bound / lower bound and optimality gap vs. nodes
  processed.
- **Bottom row** — the same metrics vs. wall-clock time.

### `compare_cg` — column generation

```bash
# compare Wentges smoothing values (fixed nb-cols=50)
python -m vrp.tests.compare_cg --instance RC101.txt --alphas 0 0.2 0.5

# compare pricing batch sizes (fixed alpha=0)
python -m vrp.tests.compare_cg --instance RC101.txt --nb-cols-list 1 5 20 50

# compare batch sizes with smoothing, save figure
python -m vrp.tests.compare_cg --instance RC101.txt --nb-cols-list 1 5 20 50 --alpha 0.3 --save cg.png

# restrict to fewer vehicles than the instance default
python -m vrp.tests.compare_cg --instance R101.txt --nb-vehicles 10 --alphas 0 0.3
```

| Flag | Default | Effect |
|------|---------|--------|
| `--alphas A …` | `0 0.1 0.3 0.5` | compare Wentges α values; nb-cols fixed at `--nb-cols` |
| `--nb-cols-list N …` | — | compare pricing batch sizes; α fixed at `--alpha` |
| `--nb-cols` | `50` | batch size used when `--alphas` is active |
| `--alpha` | `0.0` | α used when `--nb-cols-list` is active |
| `--nb-vehicles` | instance value | override vehicle count K |

`--alphas` and `--nb-cols-list` are mutually exclusive.

### `compare_bnp` — branch-and-price

```bash
# compare gap thresholds (default: exact only)
python -m vrp.tests.compare_bnp --instance RC101.txt --gaps 0 2 5

# compare pricing batch sizes
python -m vrp.tests.compare_bnp --instance RC101.txt --nb-cols-list 5 20 50

# compare Wentges smoothing values
python -m vrp.tests.compare_bnp --instance RC101.txt --alphas 0 0.3 0.5

# compare node-selection strategies
python -m vrp.tests.compare_bnp --instance RC101.txt --search both

# restrict to fewer vehicles, save figure
python -m vrp.tests.compare_bnp --instance R101.txt --nb-vehicles 10 --save bnp.png
```

| Flag | Default | Effect |
|------|---------|--------|
| `--gaps G …` | — | compare optimality-gap stop thresholds |
| `--alphas A …` | — | compare Wentges α values |
| `--nb-cols-list N …` | — | compare pricing batch sizes; gap=0, α=0 |
| `--search` | — | `depth-first`, `best-first`, or `both` |
| `--nb-cols` | `50` | batch size used for all modes except `--nb-cols-list` |
| `--nb-vehicles` | instance value | override vehicle count K |

If none of `--gaps`, `--alphas`, `--nb-cols-list`, `--search` is given, a single
exact run is plotted.

---

## 6. Troubleshooting (the five errors that always show up)

| Symptom                                   | Cause                                | Fix                                              |
|-------------------------------------------|--------------------------------------|--------------------------------------------------|
| `ImportError: highspy` / `rcspp`          | venv not active                      | `source .venv/bin/activate`                      |
| LP value `0` at iter 0                    | forgot RHS=1 on covering rows        | check EX-A.1                                     |
| Pricer returns empty                      | `pi[0]` left unset                   | force `pi[0] = 0.0` before pricing               |
| LB > LP                                   | heuristic pricer used for bound      | LB only valid with **exact** pricer              |
| LB lower than expected / slow convergence | σ not passed to pricer               | set `dual_by_id[depot_id] = sol.sigma` before pricing |
| RMH returns the LP value                  | `_set_integrality` not implemented   | finish EX-D.1                                    |

---

## 7. Going further

Bonus exercise **F** if you finish early: replace plain dominance by
**ng-routes** (Baldacci, Mingozzi, Roberti — 2011) inside `pricing.py`,
and measure the speed-up on `R101_50.txt`.

The reference solution will be published at the end of the workshop.

---

## 8. References

- J. Desrosiers, M. Lübbecke, G. Desaulniers, J.B. Gauthier,
  *Branch-and-Price*, Springer, 2026 (open access — DOI
  10.1007/978-3-031-96917-1).
- M.M. Solomon, *Algorithms for the vehicle routing and scheduling problems
  with time window constraints*, Operations Research, 35(2), 1987 (the
  benchmark instances).
- HiGHS — <https://highs.dev>.

Have fun!

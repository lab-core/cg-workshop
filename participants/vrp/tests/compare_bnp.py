"""Compare B&P progress for different gap thresholds (and optionally alpha values).

Runs branch-and-price independently for each configuration on the same
instance, then plots UB / LB convergence and the optimality gap side-by-side.

Usage::

    python -m vrp.tests.compare_bnp
    python -m vrp.tests.compare_bnp --instance R101.txt --gaps 0 2 5
    python -m vrp.tests.compare_bnp --instance R101.txt --search both --save bnp.png
    python -m vrp.tests.compare_bnp --instance R101.txt --alphas 0 0.3
"""

import argparse
import os
import signal
import sys
import time

from vrp.instance_reader import InstanceReader
from vrp.log import configure as configure_logging
from vrp.plot import plot_bnp_progress
from vrp.tests._paths import find_instance
from vrp.tests.exE_bnp import run_bnp


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Compare B&P progress for different configurations."
    )
    ap.add_argument("--instance", default="toy.txt",
                    help="instance file name (searched in known data paths)")
    ap.add_argument("--gaps", type=float, nargs="+", default=None,
                    metavar="GAP",
                    help="gap%% thresholds to compare (default: 0 — exact only)")
    ap.add_argument("--alphas", type=float, nargs="+", default=None,
                    metavar="ALPHA",
                    help="Wentges alpha values to compare (gap fixed at 0)")
    ap.add_argument("--Ks", type=int, nargs="+", default=None,
                    metavar="K",
                    help="max-columns-per-iteration values to compare (gap fixed at 0)")
    ap.add_argument("--search", choices=["depth-first", "best-first", "both"],
                    default=None,
                    help="compare depth-first vs best-first node selection")
    ap.add_argument("--K", type=int, default=50,
                    help="max columns added per pricing call, used when not "
                         "comparing Ks (default: 50)")
    ap.add_argument("--save", default=None, metavar="PATH",
                    help="save the figure to this file instead of displaying it")
    ap.add_argument("--verbose", "-v", action="store_true",
                    help="enable DEBUG logs during B&P runs")
    args = ap.parse_args()
    configure_logging(verbose=args.verbose)

    # Build the list of (label, K_MAX, gap, alpha, depth_first) configurations.
    configs: list[tuple[str, int, float, float, bool]] = []
    if args.Ks is not None:
        for k in args.Ks:
            configs.append((f"K = {k}", k, 0.0, 0.0, True))
    elif args.search is not None:
        pairs = [("depth-first", True), ("best-first", False)]
        if args.search != "both":
            pairs = [(args.search, args.search == "depth-first")]
        for lbl, df in pairs:
            configs.append((lbl, args.K, 0.0, 0.0, df))
    elif args.gaps is not None:
        for g in args.gaps:
            label = "exact" if g == 0.0 else f"gap ≤ {g}%"
            configs.append((label, args.K, g, 0.0, True))
    elif args.alphas is not None:
        for a in args.alphas:
            configs.append((f"α = {a}", args.K, 0.0, a, True))
    else:
        configs = [("exact", args.K, 0.0, 0.0, True)]

    inst = InstanceReader(find_instance(args.instance)).read()
    n_cust = len(inst.get_customers_by_id()) - 1
    print(f"Instance : {args.instance}  ({n_cust} customers)")
    print()

    runs = []
    for label, k_max, gap, alpha, df in configs:
        print(f"  {label:15s} ...", end=" ", flush=True)
        t0 = time.perf_counter()
        inc = run_bnp(inst, K_MAX=k_max, alpha=alpha, gap_pct=gap,
                      depth_first=df)
        elapsed = time.perf_counter() - t0
        n_nodes = len(inc.ub_history)
        print(f"nodes={n_nodes:4d}  cost={inc.cost:.2f}  time={elapsed:.1f}s")
        runs.append((label, inc))

    k_desc = f"K_MAX={args.K}" if args.Ks is None else f"Ks={args.Ks}"
    print()
    title = (f"B&P progress — {args.instance}  "
             f"({n_cust} customers, {k_desc})")
    plot_bnp_progress(runs, title=title, save=args.save)
    return 0


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda *_: os._exit(1))
    sys.exit(main())

"""Compare CG convergence for different alpha values or K limits.

Runs column generation independently for each configuration on the same
instance, then plots LP / LB convergence and the duality gap side-by-side.

Usage::

    python -m vrp.tests.compare_cg
    python -m vrp.tests.compare_cg --instance RC101.txt --alphas 0 0.2 0.5 0.8
    python -m vrp.tests.compare_cg --instance RC101.txt --nb-cols-list 1 5 20 50
    python -m vrp.tests.compare_cg --instance C101.txt --save cg_convergence.png
"""

import argparse
import os
import signal
import sys

from vrp.instance_reader import InstanceReader
from vrp.log import configure as configure_logging
from vrp.plot import plot_cg_convergence
from vrp.tests._paths import find_instance
from vrp.vrp import VRP


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Compare CG convergence for different configurations."
    )
    ap.add_argument("--instance", default="toy.txt",
                    help="instance file name (searched in known data paths)")

    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--alphas", type=float, nargs="+",
                      default=None,
                      metavar="ALPHA",
                      help="Wentges smoothing parameters to compare (fixed K)")
    mode.add_argument("--nb-cols-list", type=int, nargs="+",
                      default=None,
                      metavar="N",
                      help="max-columns-per-iteration values to compare (fixed alpha=0)")

    ap.add_argument("--nb-cols", type=int, default=50,
                    help="max columns added per pricing call, used when --alphas "
                         "is active (default: 50)")
    ap.add_argument("--nb-vehicles", type=int, default=None,
                    help="override vehicle count (default: use instance value)")
    ap.add_argument("--alpha", type=float, default=0.0,
                    help="Wentges alpha, used when --nb-cols-list is active (default: 0)")
    ap.add_argument("--save", default=None, metavar="PATH",
                    help="save the figure to this file instead of displaying it")
    ap.add_argument("--verbose", "-v", action="store_true",
                    help="enable DEBUG logs during CG runs")
    args = ap.parse_args()
    configure_logging(verbose=args.verbose)

    # Build (label, nb_cols, alpha) triples.
    if args.nb_cols_list is not None:
        configs = [(f"nb_cols = {k}", k, args.alpha) for k in args.nb_cols_list]
        mode_desc = f"alpha={args.alpha}"
    else:
        alphas = args.alphas if args.alphas is not None else [0.0, 0.1, 0.3, 0.5]
        configs = [(f"α = {a}", args.nb_cols, a) for a in alphas]
        mode_desc = f"nb_cols={args.nb_cols}"

    inst = InstanceReader(find_instance(args.instance)).read()
    n_cust = len(inst.get_customers_by_id()) - 1
    print(f"Instance : {args.instance}  ({n_cust} customers)")
    print(f"Mode     : {mode_desc}")
    print()

    runs = []
    for label, k_max, alpha in configs:
        print(f"  {label:12s} ...", end=" ", flush=True)
        vrp = VRP(inst, nb_cols=k_max, alpha=alpha, K=args.nb_vehicles)
        vrp.solve_cg(verbose=False)
        print(f"iters={vrp.stats.iterations:3d}  "
              f"LP={vrp.stats.final_lp:.2f}  "
              f"LB={vrp.stats.final_lb:.2f}  "
              f"cols={vrp.stats.nb_columns_added}")
        runs.append((label, vrp.stats))

    print()
    title = (f"CG convergence — {args.instance}  "
             f"({n_cust} customers, {mode_desc})")
    plot_cg_convergence(runs, title=title, save=args.save)
    return 0


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda *_: os._exit(1))
    sys.exit(main())

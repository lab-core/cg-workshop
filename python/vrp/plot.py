"""Visualisation helpers for CG and B&P convergence analysis.

Usage::

    from vrp.plot import plot_cg_convergence, plot_bnp_progress

    # After running VRP.solve_cg():
    plot_cg_convergence([("no smoothing", vrp1.stats), ("α=0.3", vrp2.stats)])

    # After running branch_and_price():
    plot_bnp_progress([("exact", inc1), ("gap=5%", inc2)])
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vrp.vrp import CGStats
    from vrp.cg.bnp import BnPIncumbent

try:
    import matplotlib.pyplot as plt
    _HAS_MPL = True
except ImportError:
    _HAS_MPL = False


def _require_matplotlib() -> None:
    if not _HAS_MPL:
        raise ImportError(
            "matplotlib is required for plotting. "
            "Install it with:  pip install matplotlib"
        )


def plot_cg_convergence(
    runs: list[tuple[str, "CGStats"]],
    title: str = "CG convergence",
    save: str | None = None,
) -> None:
    """Plot LP objective and lower bound over CG iterations for multiple runs.

    Left panel  — LP value and LB per iteration.
    Right panel — duality gap (LP − LB) / |LB| × 100 per iteration.

    Parameters
    ----------
    runs    list of ``(label, CGStats)`` pairs.
    title   figure title.
    save    if given, save the figure to this path instead of displaying it.
    """
    _require_matplotlib()

    fig, (ax_obj, ax_gap) = plt.subplots(1, 2, figsize=(12, 5))

    for label, stats in runs:
        lp = stats.lp_history
        lb = stats.lb_history
        iters = list(range(len(lp)))

        ax_obj.plot(iters, lp, marker=".", label=f"{label} — LP")
        valid_lb = [(i, v) for i, v in zip(iters, lb) if math.isfinite(v)]
        if valid_lb:
            xi, yi = zip(*valid_lb)
            ax_obj.plot(xi, yi, linestyle="--", label=f"{label} — LB")

        gaps = []
        for lp_v, lb_v in zip(lp, lb):
            if math.isfinite(lb_v) and abs(lb_v) > 1e-10:
                gaps.append(100.0 * (lp_v - lb_v) / abs(lb_v))
            else:
                gaps.append(float("nan"))
        valid_gaps = [(i, g) for i, g in enumerate(gaps) if not math.isnan(g)]
        if valid_gaps:
            xi, yi = zip(*valid_gaps)
            ax_gap.plot(xi, yi, marker=".", label=label)

    ax_obj.set_xlabel("Iteration")
    ax_obj.set_ylabel("Objective value")
    ax_obj.set_title("LP objective and lower bound")
    ax_obj.legend()
    ax_obj.grid(True, alpha=0.3)

    ax_gap.set_xlabel("Iteration")
    ax_gap.set_ylabel("Gap (%)")
    ax_gap.set_title("Duality gap  (LP − LB) / |LB| × 100")
    ax_gap.legend()
    ax_gap.grid(True, alpha=0.3)

    fig.suptitle(title)
    plt.tight_layout()
    _save_or_show(fig, save)


def plot_bnp_progress(
    runs: list[tuple[str, "BnPIncumbent"]],
    title: str = "B&P progress",
    save: str | None = None,
) -> None:
    """Plot upper and lower bounds over B&P nodes (and wall-clock time) for multiple runs.

    Top row    — UB / LB and optimality gap per node processed.
    Bottom row — same metrics vs wall-clock time (when time_history is available).

    Parameters
    ----------
    runs    list of ``(label, BnPIncumbent)`` pairs.
    title   figure title.
    save    if given, save the figure to this path instead of displaying it.
    """
    _require_matplotlib()

    has_time = any(len(inc.time_history) > 0 for _, inc in runs)
    if has_time:
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        (ax_obj, ax_gap), (ax_obj_t, ax_gap_t) = axes
    else:
        fig, (ax_obj, ax_gap) = plt.subplots(1, 2, figsize=(12, 5))
        ax_obj_t = ax_gap_t = None

    for label, inc in runs:
        ub = inc.ub_history
        lb = inc.lb_history
        t  = inc.time_history

        valid_ub = [(i, v) for i, v in enumerate(ub) if math.isfinite(v)]
        if valid_ub:
            xi, yi = zip(*valid_ub)
            ax_obj.step(xi, yi, where="post", label=f"{label} — UB")

        valid_lb = [(i, v) for i, v in enumerate(lb) if math.isfinite(v) and v > -1e9]
        if valid_lb:
            xi, yi = zip(*valid_lb)
            ax_obj.plot(xi, yi, linestyle="--", label=f"{label} — LB")

        gaps = []
        for ub_v, lb_v in zip(ub, lb):
            if math.isfinite(ub_v) and math.isfinite(lb_v) and abs(ub_v) > 1e-10:
                gaps.append(100.0 * (ub_v - lb_v) / abs(ub_v))
            else:
                gaps.append(float("nan"))
        valid_gaps = [(i, g) for i, g in enumerate(gaps) if not math.isnan(g)]
        if valid_gaps:
            xi, yi = zip(*valid_gaps)
            ax_gap.plot(xi, yi, marker=".", label=label)

        if ax_obj_t is not None and t:
            valid_ub_t = [(t[i], v) for i, v in enumerate(ub)
                          if math.isfinite(v) and i < len(t)]
            if valid_ub_t:
                xi, yi = zip(*valid_ub_t)
                ax_obj_t.step(xi, yi, where="post", label=f"{label} — UB")

            valid_lb_t = [(t[i], v) for i, v in enumerate(lb)
                          if math.isfinite(v) and v > -1e9 and i < len(t)]
            if valid_lb_t:
                xi, yi = zip(*valid_lb_t)
                ax_obj_t.plot(xi, yi, linestyle="--", label=f"{label} — LB")

            valid_gaps_t = [(t[i], g) for i, g in enumerate(gaps)
                            if not math.isnan(g) and i < len(t)]
            if valid_gaps_t:
                xi, yi = zip(*valid_gaps_t)
                ax_gap_t.plot(xi, yi, marker=".", label=label)

    ax_obj.set_xlabel("Nodes processed")
    ax_obj.set_ylabel("Objective value")
    ax_obj.set_title("Upper and lower bounds")
    ax_obj.legend()
    ax_obj.grid(True, alpha=0.3)

    ax_gap.set_xlabel("Nodes processed")
    ax_gap.set_ylabel("Gap (%)")
    ax_gap.set_title("Optimality gap  (UB − LB) / UB × 100")
    ax_gap.legend()
    ax_gap.grid(True, alpha=0.3)

    if ax_obj_t is not None:
        ax_obj_t.set_xlabel("Wall-clock time (s)")
        ax_obj_t.set_ylabel("Objective value")
        ax_obj_t.set_title("Upper and lower bounds vs time")
        ax_obj_t.legend()
        ax_obj_t.grid(True, alpha=0.3)

        ax_gap_t.set_xlabel("Wall-clock time (s)")
        ax_gap_t.set_ylabel("Gap (%)")
        ax_gap_t.set_title("Optimality gap vs time")
        ax_gap_t.legend()
        ax_gap_t.grid(True, alpha=0.3)

    fig.suptitle(title)
    plt.tight_layout()
    _save_or_show(fig, save)


def _save_or_show(fig, save: str | None) -> None:
    if save:
        fig.savefig(save, dpi=150, bbox_inches="tight")
        print(f"Figure saved to {save}")
    else:
        plt.show()
    plt.close(fig)

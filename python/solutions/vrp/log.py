"""Workshop-wide logging helper.

Usage from a check script::

    from vrp.log import configure, get_logger
    configure(verbose=args.verbose)
    log = get_logger(__name__)
    log.info("instance loaded")

The default level is INFO; ``configure(verbose=True)`` switches to DEBUG.
The format prepends a short module tag so progress for the master, the
pricer, the diving heuristic and B&P stay visually distinct in the output.

We avoid touching the *root* logger so that running several scripts in the
same process (or from a notebook) does not duplicate handlers.
"""

import logging
import sys


_PACKAGE_LOGGER = "vrp"
# Name column width: longest logger name is "vrp.pricing" (11 chars).
_FORMAT = "%(asctime)s | %(levelname)-5s | %(name)-12s | %(message)s"
_DATEFMT = "%H:%M:%S"

_BOLD  = "\033[1m"
_CYAN  = "\033[96m"
_RESET = "\033[0m"

_configured = False


class _Formatter(logging.Formatter):
    """Standard formatter; highlights vrp.bnp lines in bold cyan."""

    def format(self, record: logging.LogRecord) -> str:
        msg = super().format(record)
        if record.name.endswith(".bnp"):
            return f"{_BOLD}{_CYAN}{msg}{_RESET}"
        return msg


def configure(verbose: bool = False, level: int | None = None) -> None:
    """Configure the workshop logger.

    Parameters
    ----------
    verbose : bool, default False
        DEBUG when True, INFO otherwise. Ignored if ``level`` is provided.
    level : int, optional
        Explicit logging level (e.g. ``logging.WARNING``). Overrides ``verbose``.
    """
    global _configured

    root = logging.getLogger(_PACKAGE_LOGGER)
    if level is None:
        level = logging.DEBUG if verbose else logging.INFO
    root.setLevel(level)

    # Re-use a single handler instead of stacking new ones each time
    # ``configure`` is invoked (e.g. across multiple checks in the same
    # interpreter).
    if not _configured:
        handler = logging.StreamHandler(stream=sys.stderr)
        handler.setFormatter(_Formatter(_FORMAT, datefmt=_DATEFMT))
        root.addHandler(handler)
        root.propagate = False                # don't double-print via root
        _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a child of the ``vrp`` logger named after the calling module."""
    if name.startswith(_PACKAGE_LOGGER):
        return logging.getLogger(name)
    return logging.getLogger(f"{_PACKAGE_LOGGER}.{name}")

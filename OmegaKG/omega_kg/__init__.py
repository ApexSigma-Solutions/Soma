"""omega_kg package public API.

Provide a lightweight package-level entrypoint so callers can do

        from omega_kg import main

and get a sensible entrypoint (this delegates to the CLI).
"""

from .cli import cli as _cli  # re-exported as `main` for compatibility


def main(*args, **kwargs):
    """Package-level entrypoint.

    Delegates to the Click CLI group defined in :mod:`omega_kg.cli`.

    Having this symbol keeps the project backward-compatible with
    scripts that do ``from omega_kg import main`` (e.g. debug_start.py).
    """
    # The CLI object is a Click command group — calling it will run the CLI.
    return _cli(*args, **kwargs)


__all__ = ["main"]

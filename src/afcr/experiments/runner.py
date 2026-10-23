"""Backward-compatible entry point: ``python -m afcr.experiments.runner`` runs the full suite (see suite.py)."""
from .suite import main

if __name__ == "__main__":
    main()

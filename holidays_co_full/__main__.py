"""Permite invocar la CLI con ``python -m holidays_co_full``."""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())

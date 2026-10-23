#!/usr/bin/env python3
"""Starter entry point for the inverse maintenance planner."""

from __future__ import annotations

import sys


def main() -> int:
    if len(sys.argv) != 3:
        print("REFUSED: expected input and output paths", file=sys.stderr)
        return 2
    print("REFUSED: inverse planner is not implemented", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

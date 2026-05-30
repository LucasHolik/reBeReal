"""Allow `python -m rebereal` to invoke the CLI."""

from rebereal.cli import main

if __name__ == "__main__":
    raise SystemExit(main())

"""Serve the Brain Terminal on http://127.0.0.1:8765 (local only).

    uv run python scripts/serve_terminal.py            # this checkout's brain
    uv run python scripts/serve_terminal.py --root ../quant-agent-brain
"""

from __future__ import annotations

import argparse
import webbrowser
from pathlib import Path

import uvicorn

from quant_brain.config import PROJECT_ROOT
from quant_brain.ui.app import TerminalConfig, create_app


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=str(PROJECT_ROOT),
                        help="brain checkout to read (default: this one)")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--open", action="store_true", help="open the browser")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    config = TerminalConfig(project_root=root, brain_db=root / "db" / "brain.sqlite",
                            terminal_db=root / "db" / "terminal.sqlite", port=args.port)
    if args.open:
        webbrowser.open(f"http://127.0.0.1:{args.port}/")
    uvicorn.run(create_app(config), host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()

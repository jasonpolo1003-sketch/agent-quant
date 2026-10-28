"""Manual command-line refresh."""
import argparse
import json
from pathlib import Path
from .core import Library
from .metadata import SERIES


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, default=Path(__file__).resolve().parents[2] / 'data')
    args = parser.parse_args(argv)
    library = Library(args.data_dir)
    failed = False
    for sid in SERIES:
        result = library.refresh(sid)
        print(json.dumps(result), flush=True)
        failed |= not result['ok']
    return int(failed)


if __name__ == '__main__':
    raise SystemExit(main())

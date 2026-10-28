"""Fixed scheduler/manual entry point; never registers a task."""
from data_library.worker import main

if __name__ == '__main__':
    raise SystemExit(main(['run-once']))

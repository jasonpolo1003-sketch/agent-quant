"""OS-backed lifetime locks, shared by UI, CLI and bounded worker."""
from contextlib import contextmanager
from pathlib import Path
import portalocker


class Busy(TimeoutError):
    """An update is in progress; retry without discarding prior data."""


@contextmanager
def lock(root, name, timeout=0.5):
    path = Path(root) / 'locks' / f'{name}.lock'
    path.parent.mkdir(parents=True, exist_ok=True)
    guard = portalocker.Lock(str(path), mode='a', timeout=timeout)
    try:
        guard.acquire()
    except portalocker.exceptions.LockException as exc:
        raise Busy(f'{name}: update in progress; retry shortly') from exc
    try:
        yield
    finally:
        guard.release()

import contextlib
import os
from pathlib import Path


@contextlib.contextmanager
def working_directory(path: Path, create=True):
    """Changes working directory and returns to previous on exit."""
    prev_cwd = Path.cwd()
    if create:
        path.mkdir(exist_ok=True)
    os.chdir(str(path.absolute()))
    try:
        yield
    finally:
        os.chdir(str(prev_cwd))
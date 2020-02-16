import contextlib
import os
from collections.abc import Iterable
from pathlib import Path
from typing import Callable, List


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


class list_property:
    """Overrides assignments of list-like objects"""

    def __init__(self, fget: Callable[[object], List]):
        self.fget = fget

    def __get__(self, obj, _obj_type):
        return self.fget(obj)

    def __set__(self, obj, val):
        if not isinstance(val, Iterable) or isinstance(val, str):
            self.fget(obj).append(val)
        else:
            self.fget(obj).extend(val)

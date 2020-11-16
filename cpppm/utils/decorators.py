import os
from collections.abc import Iterable
from functools import wraps
from pathlib import Path
from typing import Callable, List, Set, Union, Mapping, Dict


def working_directory(cwd: Path, env: Dict = None, create=True):
    def decorator(func):
        @wraps(func)
        def wrapper():
            """Changes working directory and returns to previous on exit."""
            prev_cwd = Path.cwd()
            oldenv = None
            if env:
                oldenv = os.environ
                os.environ.update(env)
            if create:
                cwd.mkdir(exist_ok=True)
            os.chdir(str(cwd.absolute()))
            if oldenv:
                os.environ = oldenv
            try:
                result = func()
            finally:
                os.chdir(str(prev_cwd))
            return result
        return wrapper
    return decorator


class list_property:
    """Overrides assignments of list-like objects"""

    def __init__(self, fget: Callable[[object], Union[List, Set, Mapping]]):
        self.fget = fget

    def __get__(self, obj, _obj_type):
        return self.fget(obj)

    def __set__(self, obj, val):
        prop = self.fget(obj)
        assert type(prop) != tuple
        if isinstance(val, Iterable) and not isinstance(val, str):
            if isinstance(prop, (dict, set)):
                prop.update(val)
            else:
                prop.extend(val)
        else:
            if isinstance(prop, dict):
                prop.update(val)
            elif isinstance(prop, set):
                prop.add(val)
            else:
                prop.append(val)


class dependencies_property(list_property):

    def __set__(self, obj, val):
        if hasattr(val, 'event'):
            self.fget(obj).extend(val.event.target)
        else:
            super().__set__(obj, val)


class classproperty(property):
    def __get__(self, cls, owner):
        return classmethod(self.fget).__get__(None, owner)()


class collectable_property(list_property):
    def __init__(self, fget):
        super().__init__(fget)
        self.rget = None
        self.fget = fget

    def __get__(self, obj, obj_type):
        collected = self.fget(obj)
        collected = type(collected)(collected)
        assert type(collected) != tuple
        subs = self.rget(obj) if callable(self.rget) else self.rget.__get__(obj, type(obj))
        for sub in subs:
            assert type(sub) == obj_type
            prop = self.__get__(sub, type(sub))
            if isinstance(collected, dict) or isinstance(collected, set):
                collected.update(prop)
            else:
                collected.extend(prop)

        return collected

    def recurse(self, rget):
        self.rget = rget
        return self


def collectable(recurse):
    def decorator(fget):
        prop = collectable_property(fget)
        prop.recurse(recurse)
        return prop

    return decorator

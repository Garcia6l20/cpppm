import asyncio
import copy
import os
from collections.abc import Iterable
from functools import wraps
from pathlib import Path
from typing import Callable, List, Set, Union, Mapping, Dict

from cpppm.utils.types import type_dir


def working_directory(cwd: Path, env: Dict = None, create=True):
    def decorator(func):
        @wraps(func)
        def wrapper():
            """Changes working directory and returns to previous on exit."""
            wrapper.prev_cwd = None
            wrapper.oldenv = None

            def setup_env():
                wrapper.prev_cwd = Path.cwd()
                if env:
                    wrapper.oldenv = os.environ
                    os.environ.update(env)
                # if create:
                #     cwd.mkdir(exist_ok=True)
                # os.chdir(str(cwd.absolute()))

            def cleanup_env():
                # os.chdir(str(wrapper.prev_cwd))
                if wrapper.oldenv:
                    os.environ = wrapper.oldenv

            try:
                setup_env()
                result = func()
            finally:
                cleanup_env()
            if asyncio.iscoroutine(result):
                async def coro_wrap():
                    setup_env()
                    result2 = await result
                    cleanup_env()
                    return result2
                return coro_wrap()
            else:
                return result
        return wrapper
    return decorator


class list_property:
    """Overrides assignments of list-like objects"""

    def __init__(self, fget: Callable[[object], Union[List, Set, Mapping]]):
        self.fget = fget
        self.__on_add = None
        self.__on_get = None

    def __call__(self, *args, **kwargs):
        return self

    def __get__(self, obj, _obj_type):
        if self.__on_get:
            return [self.__on_get(obj, item) for item in self.fget(obj)]
        return self.fget(obj)

    def __set__(self, obj, items):
        prop = self.fget(obj)
        assert type(prop) != tuple
        if not (isinstance(items, Iterable) and not isinstance(items, str)):
            if not isinstance(prop, dict):
                items = {items}

        if self.__on_add:
            new_items = set()
            for item in items:
                new_item = self.__on_add(obj, item)
                new_items.add(new_item or item)
            items = new_items

        if isinstance(prop, (dict, set)):
            prop.update(items)
        else:
            prop.extend(items)

    def on_add(self, callback):
        self.__on_add = callback

    def on_get(self, callback):
        self.__on_get = callback

    @property
    def link(self):
        return self


class filter_property:
    def __init__(self, fget: Callable[[object], Union[List, Set, Mapping]]):
        self.fget = fget

    def __get__(self, instance, owner):
        return self.fget(instance)


class dependencies_property(list_property):

    def __set__(self, obj, val):
        # if hasattr(val, 'event'):
        #     self.fget(obj).extend(val.event.target)
        # else:
        super().__set__(obj, val)


class classproperty(property):
    def __get__(self, cls, owner):
        return classmethod(self.fget).__get__(None, owner)()


class CollectError(RuntimeError):
    pass


class collectable_property(list_property):

    def __init__(self, fget, rget, permissive):
        super().__init__(fget)
        self.fget = fget
        self.rget = rget
        self.permissive = permissive

    def __get__(self, obj, obj_type):

        # ensure collected object has the recursive property
        found = False
        for att in type_dir(obj_type).values():
            if hasattr(att, 'rget') and att.rget == self.rget:
                found = True
                break
        if not found:
            if self.permissive:
                return None
            raise CollectError(f'Collecting unexpected recursive type {obj_type!r}')
        collected = self.fget(obj)
        collected = type(collected)(collected)
        subs = self.rget(obj) if callable(self.rget) else self.rget.__get__(obj, type(obj))
        if isinstance(subs, list_property):
            subs = subs.__get__(obj, type(obj))
        for sub in subs:
            prop = self.__get__(sub, type(sub))
            if prop is None:
                continue
            if isinstance(collected, dict) or isinstance(collected, set):
                collected.update(prop)
            else:
                collected.extend(prop)

        return collected

    def recurse(self, rget):
        self.rget = rget
        return self


def collectable(recurse, permissive=False):
    def decorator(fget):
        return collectable_property(fget, recurse, permissive)

    return decorator

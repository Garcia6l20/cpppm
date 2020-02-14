import re
import fnmatch
from collections import Iterable
from pathlib import Path
from typing import List, Union, final
from abc import abstractmethod


class PathList(list):
    def __init__(self, path: Path):
        super().__init__()
        self.path = path

    def glob(self, pattern: str):
        self.extend(self.path.glob(pattern))

    def rglob(self, pattern: str):
        self.extend(self.path.rglob(pattern))

    def rfilter(self, pattern: str):
        pattern = fnmatch.translate(pattern)
        for path in self:
            if re.match(pattern, str(path)):
                self.remove(path)


class ListProperty(object):
    """Overrides assignments of list-like objects"""

    def __init__(self, inner_type=list):
        self.type = inner_type
        self.val = {}

    def __get__(self, obj, _obj_type):
        return self.val[obj]

    def __set__(self, obj, val):
        if isinstance(val, self.type):
            self.val[obj] = val  # initialization
        elif not isinstance(val, Iterable) or isinstance(val, str):
            self.val[obj].append(val)
        else:
            self.val[obj].extend(val)


class Target:
    sources = ListProperty(PathList)
    include_dirs = ListProperty()
    link_libraries = ListProperty()
    compile_options: ListProperty()

    def __init__(self, name: str, source_path: Path):
        super().__init__()
        self.name = name
        self.sources = PathList(source_path)
        self.include_dirs = []
        self.link_libraries = []
        self.compile_options = []

    @property
    def source_path(self):
        return self.sources.path

    @property
    @abstractmethod
    def command(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def type(self) -> str:
        return ''

    @property
    @abstractmethod
    def exe(self) -> str:
        raise NotImplementedError

import re
import fnmatch
from collections import Iterable
from pathlib import Path
from typing import List, Union
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


class Target:
    compile_options: List[str] = {}
    include_dirs: List[str] = []
    link_libraries: Union[str, 'Target']

    def __init__(self, name: str, source_path: Path):
        super().__init__()
        self.name = name
        self.sources = PathList(source_path)

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

    def __setattr__(self, key, value):
        if key == 'sources' and hasattr(self, 'sources'):
            self.sources.clear()
            if isinstance(value, Iterable):
                self.sources.extend(value)
            else:
                self.sources.append(value)
        else:
            super().__setattr__(key, value)
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


class Target:
    compile_options: List[str] = {}
    include_dirs: List[str] = []
    link_libraries: List[Union[str, 'Target']] = []

    def __init__(self, name: str, source_path: Path):
        super().__init__()
        self.name = name
        self._sources = PathList(source_path)

    @property
    def sources(self):
        return self._sources

    @sources.setter
    def sources(self, sources: Union[Iterable, str]):
        if isinstance(sources, str):
            self._sources.append(sources)
        else:
            self._sources.extend(sources)

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

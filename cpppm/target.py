import fnmatch
import re
from abc import abstractmethod
from pathlib import Path

from cpppm.utils import ListProperty


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

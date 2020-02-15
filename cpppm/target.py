from abc import abstractmethod
from pathlib import Path

from .utils.decorators import list_property
from .utils.pathlist import PathList


class Target:
    def __init__(self, name: str, root: Path):
        super().__init__()
        self.name = name
        self._sources = PathList(root)
        self._include_dirs = PathList(root)
        self._link_libraries = []
        self._compile_options = []

    @list_property
    def sources(self) -> PathList:
        return self._sources

    @list_property
    def include_dirs(self) -> PathList:
        return self._include_dirs

    @list_property
    def link_libraries(self) -> list:
        return self._link_libraries

    @list_property
    def link_libraries(self) -> list:
        return self._link_libraries

    @property
    def source_path(self) -> list:
        return self.sources.root

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

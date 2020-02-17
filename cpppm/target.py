from abc import abstractmethod
from pathlib import Path
from typing import List

from .utils.decorators import list_property
from .utils.pathlist import PathList


class Target:
    def __init__(self, name: str, source_path: Path, build_path: Path):
        from .utils.events import Event
        super().__init__()
        self.name = name
        self.export_header = None
        self._source_path = source_path
        self._build_path = build_path

        self._sources = PathList(source_path)
        self._dependencies = PathList(build_path)
        self._include_dirs = PathList(source_path)
        self._subdirs = PathList(build_path)
        self._link_libraries = []
        self._compile_options = []
        self._compile_definitions = []
        self.events: List[Event] = []

    @property
    def source_path(self) -> Path:
        return self._source_path

    @property
    def build_path(self) -> Path:
        return self._build_path

    @list_property
    def sources(self) -> PathList:
        return self._sources

    @list_property
    def dependencies(self) -> PathList:
        return self._dependencies

    @list_property
    def include_dirs(self) -> PathList:
        return self._include_dirs

    @list_property
    def subdirs(self) -> PathList:
        return self._subdirs

    @list_property
    def link_libraries(self) -> list:
        return self._link_libraries

    @list_property
    def compile_options(self) -> list:
        return self._compile_options

    @list_property
    def compile_definitions(self) -> list:
        return self._compile_definitions

    @property
    def source_path(self) -> Path:
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

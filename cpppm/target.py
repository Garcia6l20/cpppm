import re
from abc import abstractmethod
from pathlib import Path
from typing import List, Set

from .utils.decorators import list_property, dependencies_property
from .utils.pathlist import PathList


class Target:

    install = True

    def __init__(self, name: str, source_path: Path, build_path: Path, **kwargs):
        from .events import Event
        from .project import Project
        self._bin_path = Project.current_project.bin_path
        self._lib_path = Project.current_project.lib_path
        self.name = name
        self._source_path = source_path
        self._build_path = build_path
        self._header_pattern: Set[str] = {r'.*\.h((pp)|(xx)|(h))?$'}

        self._sources = PathList(source_path)
        self._dependencies = PathList(build_path)
        self._include_dirs = PathList(source_path)
        self._subdirs = PathList(build_path)
        self._link_libraries = []
        self._compile_options = []
        self._compile_definitions = []
        self.events: List[Event] = []

        if 'install' in kwargs:
            self.install = bool(kwargs['install'])

    @property
    def header_pattern(self) -> str:
        return '|'.join(pattern for pattern in self._header_pattern)

    @property
    def headers(self) -> List[Path]:
        pattern = self.header_pattern
        out: List[Path] = []
        for source in self.sources:
            if re.match(pattern, str(source)):
                out.append(source)
        return out

    @property
    def compile_sources(self) -> PathList:
        pattern = self.header_pattern
        out: List[Path] = []
        for source in self.sources:
            if not re.match(pattern, str(source)):
                out.append(source)
        return out

    @property
    def source_path(self) -> Path:
        return self._source_path

    @property
    def build_path(self) -> Path:
        return self._build_path

    @property
    def bin_path(self) -> Path:
        return self._bin_path / self.binary

    @list_property
    def sources(self) -> PathList:
        return self._sources

    @dependencies_property
    def dependencies(self) -> PathList:
        return self._dependencies

    @list_property
    def include_dirs(self) -> PathList:
        return self._include_dirs

    @property
    def include_paths(self):
        paths = self._include_dirs.paths
        for lib in self.link_libraries:
            if isinstance(lib, Target):
                paths.extend(lib.include_paths)
        return paths

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
    @abstractmethod
    def command(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def type(self) -> str:
        return ''

    @property
    @abstractmethod
    def binary(self) -> str:
        raise NotImplementedError

    @property
    def public_visibility(self) -> str:
        return 'PUBLIC'

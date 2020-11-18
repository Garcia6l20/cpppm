import copy
import re
from abc import abstractmethod
from pathlib import Path
from typing import List, Set, Tuple, Dict, Union

from .utils.decorators import list_property, dependencies_property
from .utils.pathlist import PathList


class Target:
    install = True

    def __init__(self, name: str, source_path: Path, build_path: Path, **kwargs):
        from .events import Event
        from .project import current_project
        self._bin_path = current_project().bin_path
        self._lib_path = current_project().lib_path
        self.name = name
        self._source_path = source_path
        self._build_path = build_path
        self._header_pattern: Set[str] = {r'.*\.h((pp)|(xx)|(h))?$'}

        self._sources = PathList(source_path)
        self._dependencies = PathList(build_path)
        self._include_dirs = PathList(source_path)
        self._subdirs = PathList(build_path)
        self._link_libraries = set()
        self._compile_options = set()
        self._compile_definitions = set()
        self.events: List[Event] = []

        if 'install' in kwargs:
            self.install = bool(kwargs['install'])

    @property
    def cc(self):
        from .project import Project
        return Project.cc

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
        out = PathList(self.source_path)
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
    def bin_path(self) -> Union[Path, None]:
        return self._bin_path / self.binary

    @property
    def lib_path(self) -> Union[Path, None]:
        return None

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
        paths = copy.deepcopy(self._include_dirs)
        for lib in self.link_libraries:
            if isinstance(lib, Target):
                paths.extend(lib.include_paths)
        return paths

    @list_property
    def subdirs(self) -> PathList:
        return self._subdirs

    @list_property
    def link_libraries(self) -> set:
        return self._link_libraries

    @list_property
    def compile_options(self) -> set:
        return self._compile_options

    @list_property
    def compile_definitions(self) -> set:
        return self._compile_definitions

    @property
    @abstractmethod
    def command(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def final_build_step(self, objs, data):
        raise NotImplementedError

    def build(self, force=False):
        data, outdated = self.build_deps(force=force)
        data['include_paths'].update({self.source_path, *self.include_paths.absolute()})

        outdated, objs = self.cc.compile(self.compile_sources.absolute(), self.build_path, data,
                                         force=force or outdated)
        if outdated or (self.bin_path and not self.bin_path.exists()) or (self.lib_path and not self.lib_path.exists()):
            self.final_build_step(objs, data)
            return data, True
        else:
            return data, False

    def build_deps(self, force=False) -> Tuple[Dict, bool]:
        data = {
            'libraries': set(),
            'library_paths': set(),
            'include_paths': {str(self.build_path)},
            'compile_definitions': {*self.compile_definitions},
            'compile_options': {*self.compile_options},
        }

        built = False

        from .events import generator
        for evt in self._dependencies.events:
            if isinstance(evt.event, generator):
                evt()

        for lib in self.link_libraries:
            from cpppm import Library
            if isinstance(lib, Library):
                if not lib.is_header_only:
                    p = lib.lib_path
                    data['libraries'].add(p.name)
                    data['library_paths'].add(str(p.parent))
                lib_data, built = lib.build(force=force)
                for k, v in lib_data.items():
                    data[k].update(v)
            else:
                assert isinstance(lib, str)
                if lib == 'spdlog':
                    pass
                from cpppm.project import current_project
                for path in current_project().conan_library_paths(lib):
                    data['library_paths'].add(path)
                for path in current_project().conan_include_paths(lib):
                    data['include_paths'].add(path)
                sys_libs, libs = current_project().conan_link_libraries(lib)
                for conan_lib in libs:
                    data['libraries'].add(conan_lib)
                for conan_lib in sys_libs:
                    data['libraries'].add(conan_lib)
                for definition in current_project().conan_defines(lib):
                    data['compile_definitions'].add(definition)

        return data, built

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

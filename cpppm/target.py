import asyncio
import copy
import re
from abc import abstractmethod
from pathlib import Path
from typing import List, Set, Tuple, Dict, Union

from .utils.decorators import list_property, dependencies_property, collectable
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
        self._include_dirs = PathList(source_path, build_path.absolute())
        self._library_dirs = PathList(self._lib_path, '.')
        self._subdirs = PathList(build_path)
        self._link_libraries = set()
        self._compile_options = set()
        self._compile_definitions = dict()
        self.events: List[Event] = []
        self._built = False
        self._build_lock = asyncio.Lock()

        if 'install' in kwargs:
            self.install = bool(kwargs['install'])

    @property
    def macro_name(self):
        return self.name.upper().replace('-', '_')

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

    @collectable(link_libraries, permissive=True)
    def lib_dependencies(self) -> set:
        if not hasattr(self, '_lib_dependencies'):
            self._lib_dependencies = copy.copy(self._link_libraries)
        return self._lib_dependencies

    @collectable(link_libraries, permissive=True)
    def compile_options(self) -> set:
        return self._compile_options

    @collectable(link_libraries, permissive=True)
    def compile_definitions(self) -> dict:
        return self._compile_definitions

    @collectable(link_libraries, permissive=True)
    def include_dirs(self) -> PathList:
        return self._include_dirs

    @collectable(link_libraries, permissive=True)
    def library_dirs(self) -> PathList:
        return self._library_dirs

    async def build(self, force=False):
        async with self._build_lock:
            if self._built:
                return self._built

            outdated = await self.build_deps()
            from cpppm.config import config
            return await config.toolchain.cxx_compiler.compile(self, force=force or outdated)

    async def build_deps(self) -> bool:
        definitions = set()
        for k, v in self.compile_definitions.items():
            if v is not None:
                definitions.add(f'{k}={v}')
            else:
                definitions.add(f'{k}')

        from .events import generator
        events_to_wait = set()
        for evt in self._dependencies.events:
            if isinstance(evt.event, generator):
                result = evt()
                if result and asyncio.iscoroutine(result):
                    events_to_wait.add(result)
        await asyncio.gather(*events_to_wait)

        builds = set()
        for lib in self.link_libraries:
            from cpppm import Library
            if isinstance(lib, Library):
                builds.add(lib.build())
        results = await asyncio.gather(*builds)
        built = any(results) if len(results) else False
        return built

    @property
    @abstractmethod
    def binary(self) -> str:
        raise NotImplementedError

    def __str__(self):
        return f'{self.__class__.__name__}[{self.name}]'

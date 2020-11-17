import platform
import re
from pathlib import Path
from typing import List, Set

from .target import Target


class Library(Target):
    static: bool = False

    def __init__(self, name: str, source_path: Path, build_path: Path, **kwargs):
        from . import Executable
        super().__init__(name, source_path, build_path, **kwargs)
        self.export_header = None
        self._public_pattern: Set[str] = {r'.*/include/.+'}
        self._tests: Set[Executable] = set()
        self._tests_backend: str = None

    @property
    def public_pattern(self) -> str:
        return '|'.join(pattern for pattern in self._public_pattern)

    @property
    def shared(self) -> bool:
        return not self.static

    @shared.setter
    def shared(self, value: bool):
        self.static = not value

    @property
    def type(self) -> str:
        if self.is_header_only:
            return 'INTERFACE'
        return 'STATIC' if self.static else 'SHARED'

    @property
    def command(self) -> str:
        return 'add_library'

    @property
    def lib_path(self) -> Path:
        return self._lib_path / self.library

    @property
    def bin_path(self) -> Path:
        if platform.system() == 'Windows':
            return self._bin_path / self.library
        else:
            return self._lib_path / self.library

    @property
    def library(self) -> str:
        if platform.system() == 'Linux':
            return f'lib{self.name}.{"so" if self.shared else "a"}'
        elif platform.system() == 'Windows':
            return self.name + '.lib'
        else:
            raise NotImplementedError  # TODO

    @property
    def binary(self) -> str:
        if platform.system() == 'Linux':
            return None if self.static else 'lib' + self.name + '.so'
        elif platform.system() == 'Windows':
            return None if self.static else self.name + '.dll'
        else:
            raise NotImplementedError  # TODO

    @property
    def is_header_only(self) -> bool:
        pattern = self.header_pattern
        for source in self.sources:
            if not re.match(pattern, str(source)):
                return False
        return True

    @property
    def public_headers(self) -> List[Path]:
        out: List[Path] = []
        pattern = self.public_pattern
        for header in self.headers:
            if re.match(pattern, str(header)):
                out.append(header)
        if self.export_header:
            out.append(self.build_path / Path(self.export_header))
        return out

    @property
    def public_visibility(self) -> str:
        if self.is_header_only:
            return 'INTERFACE'
        return 'PUBLIC'

    @property
    def tests(self) -> set:
        return self._tests

    def build(self):
        libraries, library_paths, include_paths, definitions = self.build_deps()

        if self.is_header_only:
            return

        objs = self.cc.compile(self.compile_sources, self.build_path,
                               include_paths=[self.source_path, *self.include_paths, *include_paths],
                               definitions=definitions)
        self.bin_path.parent.mkdir(exist_ok=True, parents=True)
        self.cc.make_library(objs, self.bin_path, library_paths=[self._lib_path, *library_paths], libraries=libraries)

    def _add_test(self, test):
        from . import Project, Executable
        if isinstance(test, Executable):
            exe = test
        else:
            assert isinstance(test, str)
            exe = Project.current_project.executable(f'{self.name}-{Path(test).stem}')
            exe.sources = test
        exe.install = False
        self._tests.add(exe)
        exe.link_libraries = self
        if self.tests_backend:
            exe.link_libraries = self.tests_backend

    @tests.setter
    def tests(self, tests):
        from . import Executable
        if isinstance(tests, str) or isinstance(tests, Executable):
            self._add_test(tests)
        else:
            for test in tests:
                self._add_test(test)

    @property
    def tests_backend(self):
        if not self._tests_backend:
            return None
        return self._tests_backend.split('/')[0]

    @tests_backend.setter
    def tests_backend(self, backend: str):
        from . import Project
        Project.current_project.build_requires = backend
        self._tests_backend = backend
        for test in self.tests:
            test.link_libraries = self.tests_backend

    def test(self):
        from . import Project
        for test in self.tests:
            Project.current_project.build(test.name)

        for test in self.tests:
            test.run()

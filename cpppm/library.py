import asyncio
import platform
import re
from pathlib import Path
from typing import Set, Union

from .target import Target
from .utils.pathlist import PathList


class Library(Target):
    static: bool = False

    def __init__(self, name: str, source_path: Path, build_path: Path, **kwargs):
        from . import Executable
        super().__init__(name, source_path, build_path, **kwargs)
        self.export_header = None
        self._public_pattern: Set[str] = {r'(.*/)?include/.+'}
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
    def lib_path(self) -> Union[Path, None]:
        if self.is_header_only:
            return None
        return self._lib_path / self.library if self._lib_path else None

    @property
    def bin_path(self) -> Union[Path, None]:
        if self.is_header_only:
            return None
        if platform.system() == 'Windows':
            return self._bin_path / self.binary
        else:
            return self._lib_path / self.library

    @property
    def library(self) -> Union[str, None]:
        if self.is_header_only:
            return None
        elif platform.system() == 'Linux':
            return f'lib{self.name}.{"so" if self.shared else "a"}'
        elif platform.system() == 'Windows':
            return self.name + '.lib'
        else:
            raise NotImplementedError  # TODO

    @property
    def binary(self) -> Union[str, None]:
        if self.is_header_only:
            return None
        elif platform.system() == 'Linux':
            return None
        elif platform.system() == 'Windows':
            return None if self.static else self.name + '.dll'
        else:
            raise NotImplementedError  # TODO

    @property
    def is_header_only(self) -> bool:
        pattern = self.header_pattern
        for source in self.sources:
            if not re.match(pattern, str(source.as_posix())):
                return False
        return True

    @property
    def public_headers(self) -> PathList:
        out = PathList(self.source_path)
        pattern = self.public_pattern
        for header in self.headers:
            if re.match(pattern, str(header.as_posix())):
                out.append(header)
        if self.export_header:
            out.append(self.build_path / Path(self.export_header))
        return out

    @property
    def tests(self) -> set:
        return self._tests

    def build(self):
        if self.is_header_only:
            return super(Library, self).build_deps()
        else:
            return super(Library, self).build()

    def _add_test(self, test):
        from . import current_project, Executable
        if isinstance(test, Executable):
            exe = test
        else:
            assert isinstance(test, str)
            exe = current_project().executable(f'{self.name}-{Path(test).stem}')
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
        from . import current_project
        current_project().build_requires = backend
        self._tests_backend = backend
        for test in self.tests:
            test.link_libraries = self.tests_backend

    async def test(self):
        from . import current_project
        builds = set()
        for test in self.tests:
            builds.add(current_project().build(test.name))
        await asyncio.gather(*builds)

        for test in self.tests:
            await test.run()

import platform
import re
from pathlib import Path
from typing import List, Pattern, Set

from cpppm.utils.decorators import list_property

from .target import Target


class Library(Target):
    static: bool = False

    def __init__(self, name: str, source_path: Path, build_path: Path, **kwargs):
        super().__init__(name, source_path, build_path, **kwargs)
        self.export_header = None
        self._header_pattern: Set[str] = {r'.*\.h(pp)?$'}
        self._public_pattern: Set[str] = {r'.*/include/.+'}

    @list_property
    def header_pattern(self) -> Set[str]:
        return self._header_pattern

    @list_property
    def public_pattern(self) -> Set[str]:
        return self._public_pattern

    @property
    def shared(self) -> bool:
        return not self.static

    @shared.setter
    def shared(self, value: bool):
        self.static = not value

    @property
    def type(self) -> str:
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
            return self._bin_path / self.binary
        else:
            return self._lib_path / self.binary

    @property
    def library(self) -> str:
        if platform.system() == 'Linux':
            return None if self.shared else 'lib' + self.name + '.a'
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
    def headers(self) -> List[Path]:
        pattern = '|'.join(pattern for pattern in self.header_pattern)
        out: List[Path] = []
        for source in self.sources:
            if re.match(pattern, str(source)):
                out.append(source)
        return out

    @property
    def public_headers(self) -> List[Path]:
        out: List[Path] = []
        pattern = '|'.join(pattern for pattern in self.public_pattern)
        for header in self.headers:
            if re.match(pattern, str(header)):
                out.append(header)
        if self.export_header:
            out.append(self.build_path / Path(self.export_header))
        return out

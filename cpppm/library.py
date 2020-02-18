import platform
import re
from pathlib import Path
from typing import List

from .target import Target


class Library(Target):
    static: bool = False

    header_pattern = r'.*\.h(pp)?$'

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
        out: List[Path] = []
        for source in self.sources:
            if re.match(Library.header_pattern, str(source)):
                out.append(source)
        return out

    @property
    def public_headers(self) -> List[Path]:
        out: List[Path] = []
        for header in self.headers:
            try:
                header.relative_to(self.source_path / 'include')
                out.append(header)
            except ValueError:
                pass
        return out

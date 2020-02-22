import collections
import os
import re
from abc import ABC, abstractmethod
from logging import Logger
from pathlib import Path
from typing import List, Type, Union, Iterable, Optional


class Layout(ABC):
    @property
    @abstractmethod
    def sources(self) -> List[str]:
        pass

    @property
    @abstractmethod
    def public_includes(self) -> List[str]:
        pass

    @public_includes.setter
    def public_includes(self, _):
        pass

    @property
    @abstractmethod
    def private_includes(self) -> List[str]:
        pass

    @property
    @abstractmethod
    def executables(self) -> List[str]:
        pass

    @property
    @abstractmethod
    def libraries(self) -> List[str]:
        pass

    @property
    @abstractmethod
    def build_modules(self) -> List[str]:
        pass


def make_dest_layout(cls: Type[Layout]) -> Type[Layout]:
    """
    Destination layouts must have only a single value for each attribute.
    @param cls: The input layout class
    @return: The wrapped destination layout class
    """

    class DestLayoutWrapper(Layout):
        pass

    for attr in (attr for attr in dir(cls) if not attr.startswith('_')):
        setattr(DestLayoutWrapper, attr, getattr(cls, attr)[:1])

    return DestLayoutWrapper


class DefaultProjectLayout(Layout):
    sources = ['src']
    public_includes = ['include', 'inline']
    private_includes = sources
    executables = ['bin']
    libraries = ['lib']
    build_modules = ['cpppm']


class DefaultDistLayout(make_dest_layout(DefaultProjectLayout)):
    pass


class UnmappedToLayoutError(Exception):
    def __init__(self, item, message = None):
        self.item = item
        if not message:
            message = f'{item} is not mapped to the source layout'
        super().__init__(message)


class LayoutConverter:
    def __init__(self, src: Type[Layout], dst: Type[Layout], anchor: Path = Path(''), root: Path = Path(''),
                 _logger: Logger = None):
        self.anchor = anchor
        self.root = root
        self.src = src
        self.dst = make_dest_layout(dst)
        self._logger = _logger

    def __call__(self, in_path: Union[Iterable, os.PathLike], anchor: Optional[Path] = None,
                 root: Optional[Path] = None):
        if not isinstance(in_path, str) and isinstance(in_path, collections.Iterable):
            return (self.__call__(p) for p in in_path if p)
        else:
            if not isinstance(in_path, Path):
                in_path = Path(in_path)
            for attr in (attr for attr in dir(self.src) if not attr.startswith('_')):
                src = getattr(self.src, attr)
                patterns = [f'(?:{re.escape(src)})' for src in src]
                pattern = rf'{self.root / "/" or ""}(?:.*)?({"|".join(patterns)})/(.*)'
                match = re.match(pattern, str(in_path.absolute()))
                if match:
                    src = match.group(1)
                    dst = getattr(self.dst, attr)[0]
                    trailing = match.group(2)
                    out_path = (root or self.root) / (anchor or self.anchor) / dst / trailing
                    if self._logger:
                        self._logger.info(f'matched: {attr}, {src} -> {dst}: {out_path}')
                    return in_path, out_path
            raise UnmappedToLayoutError(in_path)

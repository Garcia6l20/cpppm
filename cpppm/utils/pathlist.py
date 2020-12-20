import fnmatch
import re
from pathlib import Path
from typing import Iterable, List, Union


class PathList:
    def __init__(self, root: Union[property, Path, 'PathList'], *paths, obj=None):
        self.paths = set()
        self.events = []
        if isinstance(root, property):
            self._root = root
            self._root_obj = obj
            assert obj
        elif isinstance(root, PathList):
            self._root = root._root
            self.paths = root.paths
        else:
            self._root = root.resolve()
        if paths:
            self.extend(paths)

    @property
    def root(self):
        return self._root.__get__(self._root_obj) if isinstance(self._root, property) else self._root

    def glob(self, pattern: str):
        self.paths.extend(self.root.glob(pattern))

    def rglob(self, pattern: str):
        self.paths.extend(self.root.rglob(pattern))

    def rfilter(self, pattern: str):
        pattern = fnmatch.translate(pattern)
        for path in self:
            if re.match(pattern, str(path)):
                self.paths.remove(path)

    def append(self, obj) -> None:
        if isinstance(obj, (str, Path)):
            if obj in self.paths:
                return
            self.paths.add(Path(obj))
        elif hasattr(obj, 'event'):
            if obj in self.events:
                return
            self.events.append(obj)
        else:
            assert False

    def extend(self, paths: Iterable[Path]):
        if isinstance(paths, PathList):
            for p in paths:
                self.append(paths.root / p)
        else:
            for p in paths:
                self.append(p)

    def absolute(self) -> List[Path]:
        return [self.root / path.as_posix() for path in self]

    def __len__(self):
        return self.paths.__len__()

    def __getitem__(self, index) -> Path:
        return self.paths.__getitem__(index)

    def __setitem__(self, index, path: Path):
        self.paths.__setitem__(index, self.__adjust__(path))

    def __delitem__(self, index):
        self.paths.__delitem__(index)

    def __iter__(self) -> Iterable[Path]:
        return self.paths.__iter__()

    def __reversed__(self) -> Iterable[Path]:
        return self.paths.__reversed__()

    def __contains__(self, index) -> bool:
        return self.paths.__contains__(index)

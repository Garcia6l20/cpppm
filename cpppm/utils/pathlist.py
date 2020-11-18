import fnmatch
import re
from pathlib import Path
from typing import Iterable, List


class PathList:
    def __init__(self, root: Path, paths: List[Path] = None):
        super().__init__()
        self.root = root.resolve()
        self.paths = []
        self.events = []
        if paths:
            self.extend(paths)

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
            self.paths.append(Path(obj))
        elif hasattr(obj, 'event'):
            self.events.append(obj)

    def extend(self, paths: Iterable[Path]):
        for p in paths:
            self.append(p)

    def absolute(self) -> List[Path]:
        return [self.root / path for path in self]

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

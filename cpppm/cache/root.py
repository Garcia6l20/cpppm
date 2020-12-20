import pickle
from pathlib import Path

from cpppm.cache.object import CacheObject


class CacheRoot(CacheObject):

    def __init__(self, path: Path = None, clean_cache=False):

        self.__cache_path = None

        super().__init__()

        if path:
            self._init_path(path, clean=clean_cache)

    def _init_path(self, path, clean=False):
        self.__cache_path = path
        if self.cache_path.exists():
            if clean:
                self.cache_path.unlink()
            else:
                with open(self.cache_path, 'rb') as cache_file:
                    self.__setstate__(pickle.load(cache_file).__getstate__())

    def cache_save(self):
        if self.cache_dirty:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_path, 'wb') as cache_file:
                pickle.dump(self, cache_file)

    def __del__(self):
        self.cache_save()

    @property
    def cache_path(self):
        return self.__cache_path

    @property
    def cache_dirty(self):
        return hasattr(self, '_CacheRoot__cache_path') and super().cache_dirty

    def cache_reset(self):
        if self.cache_dirty:
            self.cache_path.unlink(missing_ok=True)
            super().cache_reset()

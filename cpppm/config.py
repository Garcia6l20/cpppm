import ast
import json
import os
import sys
from typing import Any

from . import get_conan, _config_option, toolchains, cache
from .toolchains.toolchain import Toolchain


class ConfigEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        if hasattr(o, '__cache_save__'):
            return o.__cache_save__()
        else:
            return super().default(o)


class ConfigItem:
    def __init__(self, name, doc_, type_):
        self.name = name
        self.doc = doc_
        self.type = type_


class Config:
    __items = {
        ConfigItem('toolchain', '''Toolchain to use (default: Resolved automatically on first call)''', Toolchain),
        ConfigItem('arch', '''Arch to use (default: Resolved automatically on first call)''', str),
        ConfigItem('build_type',
                   '''Build type (default: Release, accepted values: Release, Debug, RelWithDebInfo, MinSizeRel)''',
                   str),
        ConfigItem('libcxx', '''C++ standard library (default: 'libstdc++11')''', str),
        ConfigItem('ccache', '''Use ccache if available (default: True)''', bool),
    }

    def __init__(self):
        self.toolchain = None
        self.arch = None
        self.build_type = 'Release'
        self.libcxx = None
        self.ccache = True

        self._id = 'default'
        self._conan_compiler = None
        self._source_path = None
        self._build_path = None
        self._profile = None
        self._settings = None

    def init(self, source_path, build_root=None, settings=None):
        self._source_path = source_path
        cache.build_root = build_root or self._source_path / 'build'
        self.load(settings)

    def _config_dict(self):
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}

    @property
    def keys(self):
        return [item.name for item in Config.__items]

    @staticmethod
    def _resolve_items(keys):
        if not len(keys):
            return Config.__items
        else:
            return [it for it in Config.__items if it.name in keys]

    def doc(self, *items):
        for item in self._resolve_items(items):
            print(f'{item.name}: {item.doc}')

    def show(self, *items):
        for item in self._resolve_items(items):
            print(f'{item.name}: {getattr(self, item.name)}')

    def _path(self):
        return self._source_path / '.cpppm' / f'{self._id}.json'

    @staticmethod
    def _get_item(k):
        for item in Config.__items:
            if item.name == k:
                return item

    def set(self, *items):
        for k, v in (item.split('=') for item in items):
            if not hasattr(self, k):
                raise RuntimeError(f'No such configuration key {k}')
            item = self._get_item(k)
            if item.type != str:
                if hasattr(item.type, '__cache_load__'):
                    setattr(self, k, item.type.__cache_load__(v))
                else:
                    setattr(self, k, ast.literal_eval(v))
            else:
                setattr(self, k, v)

    def load(self, settings):
        intersection = _config_option.intersection(set(sys.argv))
        if intersection:
            self._id = sys.argv[sys.argv.index(intersection.pop()) + 1]

        path = self._path()
        if path.exists():
            for k, v in json.load(path.open('r')).items():
                setattr(self, k, v)

            self._resolve_toolchain(settings)
            return True
        else:
            self._resolve_toolchain(settings)
            self.save()
            return False

    def save(self):
        path = self._path()
        path.parent.mkdir(exist_ok=True, parents=True)
        json.dump(self._config_dict(), path.open('w'), cls=ConfigEncoder)

    def _resolve_toolchain(self, settings):
        if settings:
            id_ = f'{settings.get_safe("compiler")}-{settings.get_safe("compiler.version")}-{settings.get_safe("arch")}'
            self.toolchain = toolchains.get(id_, libcxx=settings.get_safe('compiler.libcxx'))
            self.build_type = settings.get_safe('build_type')
        elif self.toolchain is None:
            self.toolchain = toolchains.get_default()
        elif isinstance(self.toolchain, str):
            self.toolchain = toolchains.get(self.toolchain, libcxx=self.libcxx)
        assert issubclass(type(self.toolchain), Toolchain)
        self._build_path = (
                cache.build_root / f'{self.toolchain.id}-{self.build_type}').absolute()
        self.libcxx = self.libcxx or self.toolchain.libcxx
        self.arch = self.arch or self.toolchain.arch
        self.toolchain.build_type = self.build_type
        os.environ.update(self.toolchain.env)


config = Config()

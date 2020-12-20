import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

from . import _config_option, toolchains, cache
from .cache import CacheRoot, CacheAttr
from .toolchains.toolchain import Toolchain


class ConfigEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        if hasattr(o, '__cache_save__'):
            return o.__cache_save__()
        else:
            return super().default(o)


class ConfigItem:
    def __init__(self, name=None, doc_=None, type_=None, default=None, refresh=None):
        self.name = name
        self.doc = doc_
        self.type = type_
        self.__value = default
        self._refresh = refresh

    @property
    def value(self):
        return self.__value

    @value.setter
    def value(self, value):
        self.__value = value

    def __getstate__(self):
        if self.value and hasattr(self.value, '__getstate__'):
            return {
                'name': self.name,
                'value': self.value.__getstate__()
            }
        else:
            return {
                'name': self.name,
                'value': self.value
            }

    @classmethod
    def __setstate__(cls, state):
        item = config._get_item(state['name'])
        setattr(item, 'value', state['value'])
        if item.value and hasattr(item.type, '__setstate__'):
            item.value = item.type.__setstate__(item.value)
        return item

    def refresh(self, cfg):
        if self._refresh:
            getattr(cfg, self._refresh)()


def get_dict_attr(obj, attr, type_=None):
    for obj in [obj] + obj.__class__.mro():
        if attr in obj.__dict__ and (type_ is None or isinstance(obj.__dict__[attr], type_)):
            return obj.__dict__[attr]
    raise AttributeError


def config_property(key):
    def decorator():
        def fget(obj: 'Config', _owner):
            return obj._get_item(key).value

        return property(fget)

    return decorator()


class Config(CacheRoot):

    def __load_bool(self, obj):
        if isinstance(obj, str):
            return obj.lower()[0] in {'t', 'y', 'o', '1'}
        else:
            return obj

    toolchain = CacheAttr(None,
                          doc='''Toolchain to use (default: Resolved automatically on first call)''',
                          on_change='_refresh_toolchain')

    arch = CacheAttr(None,
                     doc='''Arch to use (default: Resolved automatically on first call)''',
                     on_change='_refresh_arch')

    build_type = CacheAttr('Release',
                           doc='Build type '
                               '(default: Release, accepted values: Release, Debug, RelWithDebInfo, MinSizeRel)')

    libcxx = CacheAttr('libstdc++11', doc='C++ standard library (default: "libstdc++11)')
    ccache = CacheAttr(True, doc='Use ccache if available (default: True)',
                       set_hook='_Config__load_bool')

    def __load_log_level(self, level):
        level = level.lower()
        __levels = {
            'debug': logging.DEBUG,
            'info': logging.INFO,
            'warning': logging.WARNING,
            'error': logging.ERROR,
        }
        from cpppm import _logger as cpppm_logger
        cpppm_logger.setLevel(__levels[level])
        return level

    log_level = CacheAttr('info', doc='Log lovel (debug, info, warning, error)',
                          set_hook='_Config__load_log_level')

    def __init__(self):
        self._id = 'default'
        self._conan_compiler = None
        self._source_path = None
        self._build_path = None
        self._profile = None
        self._settings = None
        self.__cache = None
        super().__init__()

    def init(self, source_path: Path, build_root: Path = None, settings=None):

        self._source_path = source_path
        cache.source_root = source_path
        cache.build_root = build_root or self._source_path / 'build'

        self._init_path(cache.source_root / '.cpppm' / 'default.cache')

        self.load(settings)

    def _config_dict(self):
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}

    @property
    def keys(self):
        return self.__cache.cache_keys

    @property
    def build_path(self):
        return cache.build_root / f'{self.toolchain.id}-{self.build_type}'

    @property
    def source_path(self):
        return self._source_path

    @property
    def build_path_property(self):
        return get_dict_attr(self, 'build_path', property)

    def doc(self, *items):
        for name, doc in self.cache_doc(*items).items():
            print(f'{name}: {doc}')

    def show(self, *items):
        for item in self.cache_keys:
            print(f'{item}: {getattr(self, item)}')

    def set(self, *items):
        for k, v in (item.split('=') for item in items):
            if not hasattr(self, k):
                raise RuntimeError(f'No such configuration key {k}')
            setattr(self, k, v)

    def _refresh_toolchain(self):
        if not isinstance(self.toolchain, Toolchain):
            self._resolve_toolchain()
        self.arch = self.toolchain.arch

    def _refresh_arch(self):
        if self.toolchain.arch != self.arch:
            self.toolchain.arch = self.arch
            self.toolchain = toolchains.get(self.toolchain.id, libcxx=self.libcxx)

    def load(self, settings):
        intersection = _config_option.intersection(set(sys.argv))
        if intersection:
            self._id = sys.argv[sys.argv.index(intersection.pop()) + 1]
        self._resolve_toolchain(settings)

    def _resolve_toolchain(self, settings=None):
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

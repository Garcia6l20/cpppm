import ast
import json
import platform
import sys

from conans.client.conf.detect import _get_compiler_and_version, _get_profile_compiler_version, detect_defaults_settings
from conans.client.profile_loader import profile_from_args

from . import get_conan, _config_option, toolchains, cache
from .toolchains.toolchain import Toolchain


class Config:
    __docs = {
        'toolchain': '''Toolchain to use (default: Resolved automatically on first call)''',
        'arch': '''Toolchain to use (default: Resolved automatically on first call)''',
        # 'cc': '''C compiler (default: 'cc')''',
        # 'cxx': '''C++ compiler (default: 'c++')''',
        # 'libcxx': '''C++ standard library (default: 'libstdc++11')''',
        # 'ccache': '''Use ccache if available (default: True)''',
    }

    def __init__(self):
        self.toolchain = None
        self.cc = 'cc'
        self.cxx = 'c++'
        self.libcxx = 'libstdc++11'
        self.ccache = True

        self._id = 'default'
        self._conan_compiler = None
        self._source_path = None
        self._build_path = None
        self._profile = None
        self._settings = None

    def init(self, source_path):
        self._source_path = source_path
        cache.build_root = self._source_path / 'build'
        self.load()

    def _config_dict(self):
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}

    def doc(self, *items):
        if not len(items):
            items = self._config_dict().keys()
        for k in items:
            print(f'{k}: {Config.__docs[k]}')

    def show(self, *items):
        if not len(items):
            items = self._config_dict().keys()
        for k in items:
            print(f'{k}: {getattr(self, k)}')

    def _path(self):
        return self._source_path / '.cpppm' / f'{self._id}.json'

    def set(self, *items):
        for k, v in (item.split('=') for item in items):
            if not hasattr(self, k):
                raise RuntimeError(f'No such configuration key {k}')
            t = type(getattr(self, k))
            if t != str:
                setattr(self, k, ast.literal_eval(v))
            else:
                setattr(self, k, v)

    def load(self):
        intersection = _config_option.intersection(set(sys.argv))
        if intersection:
            self._id = sys.argv[sys.argv.index(intersection.pop()) + 1]

        path = self._path()

        # class quiet:
        #     def success(self, *args):
        #         pass
        #
        #     def error(self, *args):
        #         pass
        #
        #     def info(self, *args):
        #         pass

        # def resolve_compiler():
        #     compiler, version = _get_compiler_and_version(quiet(), self.cc)
        #     if platform.system() == 'Windows' and self.cc == 'cc':
        #         return
        #
        #     version = _get_profile_compiler_version(compiler, version, quiet())
        #     self._conan_compiler = (compiler, version)
        #     app = get_conan().app
        #     self._profile = profile_from_args(None,
        #                                       [f'compiler={compiler}', f'compiler.version={version}',
        #                                        f'compiler.libcxx={self.libcxx}'],
        #                                       None, None, None, app.cache)
        #     self._settings = self._profile.settings
        #     self._build_path = (
        #             self._source_path / 'build' / f'{compiler}-{version}-{self._settings["arch"]}').absolute()

        if path.exists():
            for k, v in json.load(path.open('r')).items():
                setattr(self, k, v)

            self._resolve_toolchain()
            return True
        else:
            self._resolve_toolchain()
            return False

    def save(self):
        path = self._path()
        path.parent.mkdir(exist_ok=True, parents=True)
        json.dump(self._config_dict(), path.open('w'))

    def _resolve_toolchain(self):
        if self.toolchain is None:
            self.toolchain = toolchains.get_default()
        elif isinstance(self.toolchain, str):
            self.toolchain = toolchains.get(self.toolchain)
        assert issubclass(type(self.toolchain), Toolchain)
        self._build_path = (
                         self._source_path / 'build' / f'{self.toolchain.id}').absolute()


config = Config()

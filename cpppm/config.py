import json

from conans.client.conf.detect import _get_compiler_and_version, _get_profile_compiler_version, detect_defaults_settings

from . import _source_path, get_conan


class Config:
    __docs = {
        'cc': '''C compiler (default: 'cc')''',
        'cxx': '''C++ compiler (default: 'c++')''',
        'libcxx': '''C++ standard library (default: 'libstdc++11')'''
    }

    def __init__(self):
        self.cc = 'cc'
        self.cxx = 'c++'
        self.libcxx = 'libstdc++11'

        self._id = 'default'
        self._conan_compiler = None
        self._source_path = None
        self._build_path = None
        self._settings = None

    def init(self, source_path):
        self._source_path = source_path
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
            setattr(self, k, v)

    def load(self, id=None):
        self._id = id or self._id
        path = self._path()

        class quiet:
            def success(self, *args):
                pass

            def error(self, *args):
                pass

            def info(self, *args):
                pass

        def resolve_compiler():
            compiler, version = _get_compiler_and_version(quiet(), self.cc)
            version = _get_profile_compiler_version(compiler, version, quiet())
            self._conan_compiler = (compiler, version)
            app = get_conan().app
            self._settings = dict(detect_defaults_settings(app.out, app.cache.default_profile_path))
            self._settings.update({
                'compiler': compiler,
                'compiler.version': version,
                'compiler.libcxx': config.libcxx
            })
            self._build_path = (
                        self._source_path / 'build' / f'{compiler}-{version}-{self._settings["arch"]}').absolute()

        if path.exists():
            for k, v in json.load(path.open('r')).items():
                setattr(self, k, v)
            resolve_compiler()
            return True
        else:
            resolve_compiler()
            return False

    def save(self):
        path = self._path()
        path.parent.mkdir(exist_ok=True, parents=True)
        json.dump(self._config_dict(), path.open('w'))


config = Config()

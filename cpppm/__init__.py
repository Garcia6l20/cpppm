import logging
from pathlib import Path

from colorama import Fore

from conans.client.conan_api import Conan
from conans.client.conf.detect import detect_defaults_settings
from jinja2 import Environment, PackageLoader

from conans.util.conan_v2_mode import CONAN_V2_MODE_ENVVAR

import sys
import os

logging.basicConfig(level=logging.INFO)

_logger = logging.getLogger('cpppm')

_jenv = Environment(loader=PackageLoader('cpppm', 'templates'), extensions=['jinja2.ext.do'])

_output_dir_option = "--out-directory", "-o"

__build_path = None

os.environ[CONAN_V2_MODE_ENVVAR] = "1"

__conan = Conan()


def get_conan():
    if __conan.app is None:
        __conan.create_app()
    return __conan


__settings = None


def get_settings():
    global __settings
    if not __settings:
        app = get_conan().app
        __settings = dict(detect_defaults_settings(app.out, app.cache.default_profile_path))
    return __settings


def _get_build_path(source_path):
    global __build_path
    if __build_path is None:
        for opt in _output_dir_option:
            import sys
            if opt in sys.argv:
                __build_path = Path(sys.argv[sys.argv.index(opt) + 1]).absolute()
                break
        else:
            settings = get_settings()
            compiler = settings['compiler']
            compiler += '-' + settings['compiler.version']
            arch = settings['arch']
            __build_path = (source_path / 'build' / f'{compiler}-{arch}').absolute()
    return __build_path


def _get_logger(obj, ident):
    return _logger.getChild(f'{obj.__class__.__name__}({ident})')


from .cli import cli
from .project import Project
from .target import Target
from .executable import Executable
from .library import Library


def main():
    cli(standalone_mode=False)

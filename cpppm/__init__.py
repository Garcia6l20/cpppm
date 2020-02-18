import logging
from pathlib import Path

from jinja2 import Environment, PackageLoader

logging.basicConfig(level=logging.INFO)

_logger = logging.getLogger('cpppm')

_jenv = Environment(loader=PackageLoader('cpppm', 'templates'), extensions=['jinja2.ext.do'])

_output_dir_option = "--out-directory", "-o"

__build_path = None


def _get_build_path():
    global __build_path
    if __build_path is None:
        for opt in _output_dir_option:
            import sys
            if opt in sys.argv:
                __build_path = Path(sys.argv[sys.argv.index(opt) + 1]).absolute()
                break
        else:
            __build_path = (Path.cwd() / 'build-cpppm').absolute()
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

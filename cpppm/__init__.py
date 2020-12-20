import asyncio
import logging
import os

from conans.client.conan_api import Conan
try:
    from conans.util.conan_v2_mode import CONAN_V2_MODE_ENVVAR
    os.environ[CONAN_V2_MODE_ENVVAR] = "1"
except ImportError:
    pass

from jinja2 import Environment, PackageLoader

import os

logging.basicConfig(level=logging.DEBUG if 'CPPPM_DEBUG' in os.environ else logging.INFO)

_logger = logging.getLogger('cpppm')

_jenv = Environment(loader=PackageLoader('cpppm', 'templates'), extensions=['jinja2.ext.do'])

_config_option = {"--config", "-C"}

_source_path = None
__build_path = None

__conan = Conan()


def get_conan():
    if __conan.app is None:
        __conan.create_app()
    return __conan


def _get_logger(obj, ident):
    return _logger.getChild(f'{obj.__class__.__name__}({ident})')


from .cli import cli
from .project import Project, current_project, root_project
from .target import Target
from .executable import Executable
from .library import Library


async def async_main():
    res = cli(standalone_mode=False)
    if asyncio.iscoroutine(res):
        await res


def main():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(async_main())

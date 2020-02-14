import logging
import os

from jinja2 import Environment, PackageLoader

_xbuild_dir = os.path.dirname(os.path.realpath(__file__))
_logger = logging.getLogger('cpppm')
_jenv = Environment(loader=PackageLoader('cpppm', 'templates'))


def _get_logger(obj, ident):
    return _logger.getChild(f'{obj.__class__.__name__}({ident})')


from .cli import cli
from .project import Project


def main():
    cli()

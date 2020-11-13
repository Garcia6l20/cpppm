from pathlib import Path

from cpppm.utils.decorators import list_property
from cpppm.utils.pathlist import PathList


class Object:
    def __init__(self, datapath: Path = Path.cwd()):
        self._paths = PathList(datapath)

    @list_property
    def paths(self) -> PathList:
        return self._paths


def test_pathlist_listproperty_append_one():
    cwd = Path.cwd()
    obj = Object()
    obj.paths = 'pathlists.py'
    assert obj.paths[0].absolute() == cwd / 'pathlists.py'


def test_pathlist_listproperty_append_iterable():
    cwd = Path.cwd()
    obj = Object()
    obj.paths = '__init__.py', 'pathlists.py'
    assert obj.paths[0].absolute() == cwd / '__init__.py'
    assert obj.paths[1].absolute() == cwd / 'pathlists.py'


def test_pathlist_listproperty_append_one_subdir():
    datapath = Path.cwd() / '.pathlistdata'
    obj = Object(datapath)
    obj.paths = 'hello'
    assert obj.paths[0].absolute() == datapath / 'hello'


def test_pathlist_listproperty_append_iterable_subdir():
    datapath = Path.cwd()
    obj = Object(datapath)
    obj.paths = 'hello', 'world'
    assert obj.paths[0].absolute() == datapath / 'hello'
    assert obj.paths[1].absolute() == datapath / 'world'

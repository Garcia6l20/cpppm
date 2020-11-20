import copy
import unittest

from pathlib import Path

from cpppm.utils.decorators import list_property
from cpppm.utils.pathlist import PathList


class PathListTestCase(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lst = PathList(Path('/tmp'), '1', '2')

    def test_nominal(self):
        self.assertTrue(self.lst.absolute() == [Path('/tmp/1'), Path('/tmp/2')])
        lst = copy.deepcopy(self.lst)
        lst.append(Path('/usr/lib'))
        print(lst.absolute())
        self.assertTrue(lst.absolute() == [Path('/tmp/1'), Path('/tmp/2'), Path('/usr/lib')])

    def test_update_path_list(self):
        lst = copy.deepcopy(self.lst)
        lst.extend(PathList(Path('/usr'), 'lib'))
        self.assertTrue(lst.absolute() == [Path('/tmp/1'), Path('/tmp/2'), Path('/usr/lib')])



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


if __name__ == '__main__':
    unittest.main()
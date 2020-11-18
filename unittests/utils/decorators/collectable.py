import copy
import unittest
from cpppm.utils.decorators import collectable, CollectError


class CollectableBaseTestCase(unittest.TestCase):
    class Data:
        def __init__(self):
            self._l = list()
            self._s = set()
            self._d = dict()
            self._children = list()

        @property
        def children(self):
            return self._children

        @collectable(children)
        def l(self):
            return self._l

        @collectable(children)
        def s(self):
            return self._s

        @collectable(children)
        def d(self):
            return self._d

    def create_data(self, attr):
        c0 = self.Data()
        setattr(c0, attr, "01")
        setattr(c0, attr, "02")
        setattr(c0, attr, 3)
        setattr(c0, attr, 4)
        c1 = self.Data()
        c0.children.append(c1)
        setattr(c1, attr, "01")
        setattr(c1, attr, "02")
        setattr(c1, attr, 7)
        setattr(c1, attr, 8)
        c2 = self.Data()
        c1.children.append(c2)
        setattr(c2, attr, 9)
        setattr(c2, attr, 10)
        setattr(c2, attr, 11)
        setattr(c2, attr, 12)
        c3 = self.Data()
        c1.children.append(c3)
        setattr(c3, attr, 9)
        setattr(c3, attr, 10)
        setattr(c3, attr, 11)
        setattr(c3, attr, 12)

        return c0, c1, c2, c3

    def test_lists(self):
        c0, _, _, _ = self.create_data('l')
        self.assertTrue(c0.l == ["01", "02", 3, 4, "01", "02", 7, 8, 9, 10, 11, 12, 9, 10, 11, 12])

    def test_set(self):
        c0, _, _, _ = self.create_data('s')
        self.assertTrue(c0.s == {"01", "02", 3, 4, 7, 8, 9, 10, 11, 12})

    def test_dict(self):
        c0 = self.Data()
        c0.d = {1: 2}
        c1 = self.Data()
        c0.children.append(c1)
        c1.d = {2: 2}
        c1.d = {3: 2}
        self.assertTrue(c0.d == {1: 2, 2: 2, 3: 2})


class CollectableVariadicTestCase(unittest.TestCase):
    class BaseData:
        def __init__(self, *args):
            self._children = list()
            self._data = args or list()

        @property
        def children(self):
            return self._children

        @collectable(children)
        def data(self):
            return self._data

        @collectable(children, permissive=True)
        def permissive_data(self):
            return self._data

    class SubData(BaseData):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tested = self.BaseData()
        self.tested.children.append(self.BaseData(1, 2))
        self.tested.children.append(self.BaseData(3, 4))
        sub = self.BaseData()
        self.tested.children.append(self.BaseData(5, 6))
        self.tested.children.append(self.BaseData(7, 8))
        self.tested.children.append(sub)

    def test_nominal(self):
        self.assertTrue(self.tested.data == [1, 2, 3, 4, 5, 6, 7, 8])

    def test_permissive(self):
        tested = copy.deepcopy(self.tested)
        tested.children.extend({'one', 'two'})
        # non-permissive collectable shall raise an error
        self.assertRaises(CollectError, lambda: tested.data)
        # permissive collectable shall skip non-accepted types
        self.assertTrue(tested.permissive_data == [1, 2, 3, 4, 5, 6, 7, 8])

    def test_sub_data(self):
        tested = copy.deepcopy(self.tested)
        tested.children.append(self.SubData('hello', 'world'))
        # permissive collectable shall skip non-accepted types
        self.assertTrue(tested.data == [1, 2, 3, 4, 5, 6, 7, 8, 'hello', 'world'])


if __name__ == '__main__':
    unittest.main()

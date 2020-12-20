import unittest

from cpppm.utils.decorators import list_property


class Class:
    def __init__(self):
        self._list = []

    @list_property
    def list(self):
        return self._list

    @list.on_add
    def __item_added(self, item):
        print(item)


class BaseTargetTestCase(unittest.TestCase):
    def test_hello_world(self):
        test = Class()
        test.list = 'hello'
        test.list = 'world'
        self.assertTrue('hello' == test.list[0])
        self.assertTrue('world' == test.list[1])


if __name__ == '__main__':
    unittest.main()

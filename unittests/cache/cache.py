import unittest
from pathlib import Path

from cpppm.cache import CacheRoot, CacheObject, CacheAttr
from unittests.test_utils import BuildTestCase, TmpDirTestCase


class SimpleRoot(CacheRoot):
    param1 = CacheAttr(None)
    param2 = CacheAttr(None)

    def __init__(self, clean_cache=False):
        super(SimpleRoot, self).__init__(Path('SimpleRoot.cache'), clean_cache=clean_cache)


class CacheObject1(CacheObject):
    value1 = CacheAttr(None)
    value2 = CacheAttr(None)


class ComplexRoot(CacheRoot):
    obj1 = CacheAttr(CacheObject1())

    def __init__(self, clean_cache=False):
        super(ComplexRoot, self).__init__(Path('ComplexRoot.cache'), clean_cache=clean_cache)


class BasicCacheTestCase(TmpDirTestCase, unittest.TestCase):

    def test_nominal(self):
        c1 = SimpleRoot(clean_cache=True)
        self.assertTrue(c1.param1 is None)
        self.assertTrue(c1.param2 is None)
        c1.param1 = 'hello'
        c1.param2 = 'world'
        c1.cache_save()
        c1 = SimpleRoot()
        self.assertTrue(c1.param1 == 'hello')
        self.assertTrue(c1.param2 == 'world')
        c1.cache_reset()
        self.assertTrue(c1.param1 is None)
        self.assertTrue(c1.param2 is None)
        c1 = SimpleRoot()
        self.assertTrue(c1.param1 is None)
        self.assertTrue(c1.param2 is None)

    def test_complex(self):
        c1 = ComplexRoot(clean_cache=True)
        self.assertTrue(c1.obj1.value1 is None)
        self.assertTrue(c1.obj1.value2 is None)
        c1.obj1.value1 = 'hello'
        c1.obj1.value2 = 'world'
        self.assertTrue(c1.obj1.value1 == 'hello')
        self.assertTrue(c1.obj1.value2 == 'world')
        c1.cache_save()
        c1 = ComplexRoot()
        self.assertTrue(c1.obj1.value1 == 'hello')
        self.assertTrue(c1.obj1.value2 == 'world')
        c1.cache_reset()
        self.assertTrue(c1.obj1.value1 is None)
        self.assertTrue(c1.obj1.value2 is None)
        c1 = ComplexRoot()
        self.assertTrue(c1.obj1.value1 is None)
        self.assertTrue(c1.obj1.value2 is None)


if __name__ == '__main__':
    unittest.main(failfast=True)

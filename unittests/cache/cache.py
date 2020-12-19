import copy
import functools
import pickle
import tempfile
import unittest
from pathlib import Path
from typing import Union, Dict

from cpppm.cache.data import CacheData
from cpppm.config import config
from cpppm.utils.inspect import instantiation_path
from unittests.test_utils import BuildTestCase, TmpDirTestCase


class CacheAttr:

    def __init__(self, default):
        self.__type = type(default)
        self.__default = copy.deepcopy(default)
        self.__value = default

    @property
    def value(self):
        return self.__value

    @value.setter
    def value(self, v):
        self.__value = v

    def __getstate__(self):
        if hasattr(self.__type, '__getstate__'):
            return {'value': pickle.dumps(self.__value),
                    'default': pickle.dumps(self.__default)}
        else:
            return {'value': self.__value,
                    'default': self.__default}

    def __setstate__(self, state):
        setattr(self, '_CacheAttr__value', state['value'])
        setattr(self, '_CacheAttr__default', state['default'])
        if isinstance(self.__value, bytes):
            self.__value = pickle.loads(self.__value)
        if isinstance(self.__default, bytes):
            self.__default = pickle.loads(self.__default)
        self.__type = type(self.__default)

    def reset(self):
        self.__value = self.__default


class CacheObject:

    def __cache_initialized__(self):
        return hasattr(self, '_CacheObject__cache_data')

    def __init__(self, clean_cache=False):
        self.__cache_dirty = True
        cls = self.__class__

        # turn attribute into property
        def _get(item: str, obj):
            if obj.__cache_initialized__():
                return obj.__cache_data[item].value
            else:
                # uninitialized subclass
                return getattr(obj, item)

        def _set(item: str, obj, val):
            if not isinstance(val, CacheAttr):
                obj.__cache_dirty = True
                obj.__cache_data[item].value = val
            else:
                if not obj.__cache_initialized__():
                    obj.__cache_data = dict()
                obj.__cache_data[item] = val

        def create_properties(keys):
            for k in [k for k in keys if k not in self.__cache_data]:
                self.__cache_data[k] = getattr(self, k)
                setattr(cls, k, property(functools.partial(_get, k),
                                         functools.partial(_set, k)))

        if not self.__cache_initialized__():
            self.__cache_data = dict()
            setattr(cls, '__cache_keys', [k for k in self.__dict__.keys() if isinstance(getattr(self, k), CacheAttr)])
            create_properties(getattr(cls, '__cache_keys'))

    @property
    def cache_dirty(self):
        return self.__cache_dirty

    def cache_reset(self):
        for item in self.__cache_data.values():
            item.reset()
        self.__cache_dirty = True

    def __setstate__(self, state):
        self.__cache_data = state
        self.__cache_dirty = False

    def __getstate__(self):
        return self.__cache_data


class CacheRoot(CacheObject):

    def __init__(self, path: Path, clean_cache=False):

        super().__init__(clean_cache)

        self.__cache_path = path

        if self.__cache_path.exists():
            if clean_cache:
                self.__cache_path.unlink()
            else:
                with open(self.__cache_path, 'rb') as cache_file:
                    self.__setstate__(pickle.load(cache_file).__getstate__())

    def cache_save(self):
        if self.cache_dirty:
            self.__cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.__cache_path, 'wb') as cache_file:
                pickle.dump(self, cache_file)

    def __del__(self):
        self.cache_save()

    def cache_reset(self):
        self.__cache_path.unlink(missing_ok=True)
        super().cache_reset()


class SimpleRoot(CacheRoot):
    def __init__(self, clean_cache=False):
        self.param1 = CacheAttr(None)
        self.param2 = CacheAttr(None)
        super(SimpleRoot, self).__init__(Path('SimpleRoot.cache'), clean_cache=clean_cache)


class CacheObject1(CacheObject):
    def __init__(self):
        self.value1 = CacheAttr(None)
        self.value2 = CacheAttr(None)
        super().__init__()


class ComplexRoot(CacheRoot):
    def __init__(self, clean_cache=False):
        self.obj1 = CacheAttr(CacheObject1())

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


#
# class CacheTestCase(BuildTestCase):
#
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, clean_cache=True, **kwargs)
#
#     def test_nominal(self):
#         c1 = CacheData(Path('cache-test.json'), {
#             'param': True
#         })
#         del c1
#         c1 = CacheData(Path('cache-test.json'), {
#             'param': False
#         })
#         self.assertTrue(c1.get('param'))
#
#     class Test:
#         def __init__(self, param=False):
#             self.param = param
#
#         def __cache_load__(self, data):
#             self.param = data['param']
#             return self
#
#         def __cache_save__(self):
#             return {
#                 'param': self.param
#             }
#
#     def test_class(self):
#
#         c1 = CacheData(Path('cache-test-class.json'), {
#             'test': self.Test()
#         })
#         c1.get('test').param = True
#         del c1
#         c1 = CacheData(Path('cache-test-class.json'), {
#             'param': self.Test()
#         })
#         self.assertTrue(c1.get('test').param)


if __name__ == '__main__':
    unittest.main(failfast=True)

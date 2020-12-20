import copy
import functools

from cpppm.cache.attr import CacheAttr


class CacheObject:
    class __CacheProperty(property):
        def __init__(self, fget, fset, data):
            super().__init__(fget, fset)
            self.data = copy.deepcopy(data)

    def __cache_initialized__(self):
        return hasattr(self, '_CacheObject__cache_data')

    def __init__(self):
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
                if obj.__cache_data[item].set_hook:
                    val = getattr(obj, obj.__cache_data[item].set_hook)(val)
                obj.__cache_data[item].value = val
                if obj.__cache_data[item].on_change:
                    getattr(obj, obj.__cache_data[item].on_change)()
            else:
                if not obj.__cache_initialized__():
                    obj.__cache_data = dict()
                obj.__cache_data[item] = val

        def create_properties(keys):
            for k in [k for k in keys if k not in self.__cache_data]:
                if k in cls.__dict__ and isinstance(cls.__dict__[k], self.__CacheProperty):
                    self.__cache_data[k] = cls.__dict__[k].data
                else:
                    self.__cache_data[k] = getattr(self, k)
                    setattr(cls, k, self.__CacheProperty(functools.partial(_get, k),
                                                         functools.partial(_set, k),
                                                         self.__cache_data[k]))

        if not self.__cache_initialized__():
            self.__cache_data = dict()
            setattr(cls, '__cache_keys', [k for k in self.__dict__.keys() if (isinstance(getattr(self, k), CacheAttr)
                                                                              or isinstance(getattr(self, k),
                                                                                            self.__CacheProperty))])
            getattr(cls, '__cache_keys').extend(
                [k for k in cls.__dict__.keys() if (isinstance(getattr(cls, k), CacheAttr)
                                                    or isinstance(getattr(cls, k),
                                                                  self.__CacheProperty))])
            create_properties(getattr(cls, '__cache_keys'))

    @property
    def cache_dirty(self):
        return self.__cache_dirty

    @property
    def cache_keys(self):
        return getattr(self.__class__, '__cache_keys')

    def cache_reset(self):
        for item in self.__cache_data.values():
            item.reset()
        self.__cache_dirty = True

    def cache_doc(self, *items):
        docs = dict()
        for k in items or self.cache_keys:
            if self.__cache_data[k].doc:
                docs[k] = self.__cache_data[k].doc
            else:
                docs[k] = 'Undocumented'
        return docs

    def __setstate__(self, state):
        self.__cache_data = state
        self.__cache_dirty = False

    def __getstate__(self):
        return self.__cache_data

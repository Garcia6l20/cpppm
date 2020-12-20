import copy
import pickle


class CacheAttr:

    def __init__(self, default, doc=None, on_change=None, set_hook=None):
        self.__type = type(default)
        self.__default = copy.deepcopy(default)
        self.__value = default
        self.doc = doc
        self.on_change = on_change
        self.set_hook = set_hook

    @property
    def value(self):
        return self.__value

    @value.setter
    def value(self, v):
        self.__value = v

    def __getstate__(self):
        if hasattr(self.__type, '__getstate__'):
            data = {'value': pickle.dumps(self.__value),
                    'default': pickle.dumps(self.__default)}
        else:
            data = {'value': self.__value,
                    'default': self.__default}
        if self.on_change:
            data['on_change'] = self.on_change

        if self.set_hook:
            data['set_hook'] = self.set_hook

        if self.doc:
            data['doc'] = self.doc

        return data

    def __setstate__(self, state):
        setattr(self, '_CacheAttr__value', state['value'])
        setattr(self, '_CacheAttr__default', state['default'])
        setattr(self, 'doc', state['doc'] if 'doc' in state else None)
        setattr(self, 'on_change', state['on_change'] if 'on_change' in state else None)
        setattr(self, 'set_hook', state['set_hook'] if 'set_hook' in state else None)
        if isinstance(self.__value, bytes):
            self.__value = pickle.loads(self.__value)
        if isinstance(self.__default, bytes):
            self.__default = pickle.loads(self.__default)
        self.__type = type(self.__default)

    def reset(self):
        self.__value = self.__default
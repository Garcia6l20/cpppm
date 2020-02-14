from collections import Iterable


class ListProperty(object):
    """Overrides assignments of list-like objects"""

    def __init__(self, inner_type=list):
        self.type = inner_type
        self.val = {}

    def __get__(self, obj, _obj_type):
        return self.val[obj]

    def __set__(self, obj, val):
        if isinstance(val, self.type):
            self.val[obj] = val  # initialization
        elif not isinstance(val, Iterable) or isinstance(val, str):
            self.val[obj].append(val)
        else:
            self.val[obj].extend(val)

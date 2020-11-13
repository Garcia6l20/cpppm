from cpppm.utils.decorators import collectable


class Data:

    def __init__(self):
        self._l = list()
        self._s = set()
        self._d = dict()
        self._childs = []

    @property
    def childs(self):
        return self._childs

    @collectable(childs)
    def l(self):
        return self._l

    @collectable(childs)
    def s(self):
        return self._s

    @collectable(childs)
    def d(self):
        return self._d


def create_data(attr):
    c0 = Data()
    setattr(c0, attr, "01")
    setattr(c0, attr, "02")
    setattr(c0, attr, 3)
    setattr(c0, attr, 4)
    c1 = Data()
    c0.childs.append(c1)
    setattr(c1, attr, "01")
    setattr(c1, attr, "02")
    setattr(c1, attr, 7)
    setattr(c1, attr, 8)
    c2 = Data()
    c1.childs.append(c2)
    setattr(c2, attr, 9)
    setattr(c2, attr, 10)
    setattr(c2, attr, 11)
    setattr(c2, attr, 12)
    c3 = Data()
    c1.childs.append(c3)
    setattr(c3, attr, 9)
    setattr(c3, attr, 10)
    setattr(c3, attr, 11)
    setattr(c3, attr, 12)

    return c0, c1, c2, c3


def test_lists():
    c0, _, _, _ = create_data('l')
    assert c0.l == ["01", "02", 3, 4, "01", "02", 7, 8, 9, 10, 11, 12, 9, 10, 11, 12]


def test_set():
    c0, _, _, _ = create_data('s')
    assert c0.s == {"01", "02", 3, 4, 7, 8, 9, 10, 11, 12}


def test_dict():
    c0 = Data()
    c0.d = {1: 2}
    c1 = Data()
    c0._childs.append(c1)
    c1.d = {2: 2}
    c1.d = {3: 2}
    assert c0.d == {1: 2, 2: 2, 3: 2}


if __name__ == '__main__':
    test_lists()

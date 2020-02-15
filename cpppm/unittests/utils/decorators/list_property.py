from cpppm.utils.decorators import list_property


class Class:
    def __init__(self):
        self._list = []

    @list_property
    def list(self):
        return self._list


def test_hello_world():
    test = Class()
    test.list = 'hello'
    test.list = 'world'
    assert 'hello' == test.list[0]
    assert 'world' == test.list[1]

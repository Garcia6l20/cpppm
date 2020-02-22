import logging
from pathlib import Path

from cpppm.layout import LayoutConverter, DefaultProjectLayout, DefaultDistLayout

logging.basicConfig(level=logging.DEBUG)


def test_default_project_to_default_dist():
    conv = LayoutConverter(DefaultProjectLayout, DefaultDistLayout, _logger=logging.getLogger(__name__))
    print(conv('include/test.hpp'))
    print(conv('include/lvl1/test.hpp'))
    print(conv('/full/path/to/include/test.hpp'))
    assert conv('include/test.hpp')[1] == Path('dist/include/test.hpp')
    assert conv('/full/path/to/include/test.hpp')[1] == Path('dist/include/test.hpp')
    assert conv('include/lvl1/test.hpp')[1] == Path('dist/include/lvl1/test.hpp')
    assert conv('/full/path/to/include/lvl1/test.hpp')[1] == Path('dist/include/lvl1/test.hpp')

    print([p for p in conv(['include/test.hpp', 'include/test2.hpp'])])
    # assert list(conv(['include/test.hpp', 'include/test2.hpp'])) == [Path('dist/include/test.hpp'), Path('dist/include/test2.hpp')]

    conv.anchor = Path('../output')
    assert conv('include/test.hpp')[1] == conv.anchor / Path('dist/include/test.hpp')
    assert conv('/full/path/to/include/test.hpp')[1] == conv.anchor / Path('dist/include/test.hpp')
    assert conv('include/lvl1/test.hpp')[1] == conv.anchor / Path('dist/include/lvl1/test.hpp')
    assert conv('/full/path/to/include/lvl1/test.hpp')[1] == conv.anchor / Path('dist/include/lvl1/test.hpp')
    assert conv('/full/path/to/include/1/2/3/4/5/6/7/8/9/test.hpp')[1] == conv.anchor / Path('dist/include/1/2/3/4/5/6/7/8/9/test.hpp')


def test_custom_project_to_default_dist():
    class CustomLayout(DefaultProjectLayout):
        public_includes = DefaultProjectLayout.public_includes + ['inline']

    conv = LayoutConverter(CustomLayout, DefaultDistLayout, _logger=logging.getLogger(__name__))

    print(conv('inline/test.inl'))
    print(conv('inline/lvl1/test.inl'))
    print(conv('/full/path/to/inline/test.inl'))

    assert conv('inline/test.inl')[1] == Path('dist/include/test.inl')
    assert conv('/full/path/to/inline/test.inl')[1] == Path('dist/include/test.inl')
    assert conv('inline/lvl1/test.inl')[1] == Path('dist/include/lvl1/test.inl')
    assert conv('/full/path/to/inline/lvl1/test.inl')[1] == Path('dist/include/lvl1/test.inl')


if __name__ == '__main__':
    test_default_project_to_default_dist()
    test_custom_project_to_default_dist()

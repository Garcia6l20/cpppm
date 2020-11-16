import logging
from pathlib import Path
import os

from cpppm import _logger
from cpppm.build.compiler import get_compiler
from cpppm.utils import Runner

__this_path = Path(os.path.realpath(__file__)).parent


def test_get_compiler():
    print(get_compiler().executable)
    print(get_compiler('gcc').executable)
    print(get_compiler('clang-10').executable)
    print(get_compiler('/usr/bin/gcc').executable)


def test_compile():
    cc = get_compiler('c++')
    cc.compile(__this_path / 'test.cc', __this_path, force=True)
    cc.link([__this_path / 'test.o'], __this_path / 'test')
    print('commands:\n -', "\n -".join(cc.commands))
    assert Runner(__this_path / 'test').run() == 0


def test_lib(shared=False):
    output_lib = __this_path / f'liblib.{"so" if shared else "a"}'
    cc = get_compiler('c++')
    cc.compile(__this_path / 'lib.cc', __this_path,
               include_paths=[__this_path],
               force=True)
    cc.make_library([__this_path / 'lib.o'], output_lib)
    cc.compile(__this_path / 'test_lib.cc', __this_path,
               include_paths=[__this_path],
               force=True)
    cc.link([__this_path / 'test_lib.o'], __this_path / 'test_lib',
            library_paths=[__this_path],
            libraries=[output_lib.name])
    print('commands:\n -', "\n -".join(cc.commands))
    assert Runner(__this_path / 'test_lib').run() == 0


if __name__ == '__main__':
    _logger.setLevel(logging.DEBUG)
    test_get_compiler()
    test_compile()
    test_lib()
    # test_lib(True)

import asyncio
import os
import tempfile
from pathlib import Path

from cpppm.config import config


def check_compiles(source, flags=None, toolchain=None, lang='cxx'):
    toolchain = toolchain or config.toolchain
    cxx_compiler = toolchain.cxx_compiler
    f = tempfile.NamedTemporaryFile('w', suffix=f'.{lang}', delete=False)
    f.write(source)
    f.close()
    loop = asyncio.get_event_loop()
    res, out, err = loop.run_until_complete(
        cxx_compiler.compile_object(Path(f.name), Path(tempfile.gettempdir()), flags, test=True))
    os.remove(f.name)
    return res == 0


def has_includes(*includes, flags=None, toolchain=None, lang='cxx'):
    src = ''
    for include in includes:
        src += f'#include <{include}>\n'
    return check_compiles(src, flags, toolchain, lang)


def has_flags(*flags, toolchain=None, lang='cxx'):
    src = ''
    return check_compiles(src, flags, toolchain, lang)

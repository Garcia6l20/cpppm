import platform
import re

from cpppm.toolchains import toolchain


def _find_gcc_toolchains(archs=None, version=None, **kwargs):
    return toolchain.find_unix_toolchains('gcc', 'g++', 'gdb', archs=archs, version=version, **kwargs)


def _find_clang_toolchains(archs=None, version=None, **kwargs):
    return toolchain.find_unix_toolchains('clang', 'clang++', 'lldb', tools_prefix='llvm', archs=archs, version=version,
                                          **kwargs)


_toolchain_finders = dict()
if platform.system() == 'Windows':
    from cpppm.toolchains import msvc

    _toolchain_finders['msvc'] = msvc.find_msvc_toolchains
    _toolchain_finders['Visual Studio'] = msvc.find_msvc_toolchains
else:
    _toolchain_finders.update({
        'gcc': _find_gcc_toolchains,
        'clang': _find_clang_toolchains
    })


def toolchain_keys():
    return _toolchain_finders.keys()


def available_toolchains(name=None, version=None, archs=None):
    toolchains = set()
    if not name:
        for find in _toolchain_finders.values():
            toolchains.update(find(version=version, archs=archs))
    else:
        toolchains.update(_toolchain_finders[name](version=version, archs=archs))
    return toolchains


def get_default():
    for find in _toolchain_finders.values():
        toolchain_ = find().pop()
        if toolchain_:
            return toolchain_


def get(toolchain_id, **kwargs):
    id_ = toolchain.ToolchainId(toolchain_id)
    return _toolchain_finders[id_.name](version=id_.version, archs=[id_.arch], **kwargs).pop()

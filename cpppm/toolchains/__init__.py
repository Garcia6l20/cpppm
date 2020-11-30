import platform

from cpppm.toolchains import toolchain


def _find_gcc_toolchains(version=None):
    return toolchain.find_unix_toolchains('gcc', 'g++', 'gdb', version=version)


def _find_clang_toolchains(version=None):
    return toolchain.find_unix_toolchains('clang', 'clang++', 'lldb', tools_prefix='llvm', version=version)


_toolchain_finders = dict()
if platform.system() == 'Windows':
    from cpppm.toolchains import msvc
    _toolchain_finders['msvc'] = msvc.find_msvc_toolchains
else:
    _toolchain_finders.update({
        'gcc': _find_gcc_toolchains,
        'clang': _find_clang_toolchains
    })


def available_toolchains(name=None, version=None):
    toolchains = set()
    if not name:
        for find in _toolchain_finders.values():
            toolchains.update(find(version))
    else:
        toolchains.update(_toolchain_finders[name](version))
    return toolchains


if __name__ == '__main__':
    print(f'{available_toolchains()}')


def get_default():
    for find in _toolchain_finders.values():
        toolchain_ = find().pop()
        if toolchain_:
            return toolchain_


def get(toolchain_id):
    id_ = toolchain.ToolchainId(toolchain_id)
    _toolchain_finders[toolchain](arch)
    return None
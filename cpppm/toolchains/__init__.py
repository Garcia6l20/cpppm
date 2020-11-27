from cpppm.toolchains import toolchain


def _find_gcc_toolchains(version=None):
    return toolchain.find_unix_toolchains('gcc', 'g++', 'gdb', version=version)


def _find_clang_toolchains(version=None):
    return toolchain.find_unix_toolchains('clang', 'clang++', 'lldb', tools_prefix='llvm', version=version)


_toolchain_finders = {
    'gcc': _find_gcc_toolchains,
    'clang': _find_clang_toolchains
}


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

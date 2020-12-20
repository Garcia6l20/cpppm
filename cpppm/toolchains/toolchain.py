import logging
import re
import shutil
from pathlib import Path

from semantic_version import SimpleSpec, Version

from cpppm import detect
from cpppm.detect import find_executables


class ToolchainId:
    expr = re.compile(r'(?P<name>[\w ]+)-(?P<version>[\d\.]+)-(?P<arch>[\w\d]+)')

    def __init__(self, id_):
        m = ToolchainId.expr.match(id_)
        if not m:
            raise RuntimeError(f'Invalid toolchain id: {id_} (must match regex "{ToolchainId.expr!r}")')
        self.name = m.group('name')
        self.version = m.group('version')
        self.arch = m.group('arch')


class Toolchain:
    def __init__(self, name, version, arch, cc, cxx, as_, ar, link, nm=None, ex=None, strip=None, dbg=None,
                 libcxx=None, c_flags=None, cxx_flags=None, link_flags=None, compiler_class=None, env=None):
        self.name = name
        self.__version = version
        self.arch = arch
        self.cc = cc
        self.cxx = cxx
        self.as_ = as_
        self.nm = nm
        self.ar = ar
        self.link = link
        self.ex = ex
        self.strip = strip
        self.dbg = dbg
        self.c_flags = c_flags or []
        self.cxx_flags = cxx_flags or []
        self.link_flags = link_flags or []
        self.compiler_class = compiler_class
        self._build_type = None
        self.conan_profile = None
        self.conan_settings = None
        if libcxx:
            m = re.match(r'(\w+c\+\+)(\d+)', libcxx)
            if m:
                self.libcxx = m.group(1)
                self.libcxx_abi_version = m.group(2)
            else:
                self.libcxx = libcxx
                self.libcxx_abi_version = ''
            if self.name == 'clang':
                flag = f'-stdlib={self.libcxx}'
                self.link_flags.append(flag)
                self.cxx_flags.append(flag)
        else:
            self.libcxx = None
        self.env = {
            'CC': str(self.cc),
            'CXX': str(self.cxx),
            'CFLAGS': ' '.join(self.c_flags),
            'CXXFLAGS': ' '.join(self.cxx_flags),
            'LDFLAGS': ' '.join(self.link_flags)
        }
        if env:
            self.env.update(env)
        self.env_list = []
        for k, v in self.env.items():
            self.env_list.append(f'{k}={v}')

    @property
    def conan_version(self):
        return self.__version.major

    @property
    def build_type(self):
        return self._build_type

    @build_type.setter
    def build_type(self, value):
        flags = self.compiler_class.build_type_flags[value]
        self.cxx_flags.extend(flags)
        self.c_flags.extend(flags)
        self._build_type = value

        from cpppm import get_conan
        from conans.client.profile_loader import profile_from_args
        app = get_conan().app
        profile_args = [f'compiler={self.name}',
                        f'compiler.version={self.conan_version}',
                        f'build_type={self._build_type}',
                        f'arch={self.arch}']
        if self.libcxx:
            profile_args.append(f'compiler.libcxx={self.libcxx}{self.libcxx_abi_version}')
        self.conan_profile = profile_from_args(None,
                                               profile_args,
                                               None, self.env_list, None, app.cache)
        self.conan_settings = self.conan_profile.settings

    @property
    def version(self):
        return self.__version

    @property
    def major(self):
        return self.__version.major

    @property
    def id(self):
        return f'{self.name}-{self.conan_version}-{self.arch}'

    def __hash__(self):
        return self.id.__hash__()

    def __eq__(self, other):
        if isinstance(other, Toolchain):
            return other.id == self.id
        else:
            return super().__eq__(other)

    @property
    def cxx_compiler(self):
        return self.compiler_class(self)

    @property
    def object_suffix(self):
        return self.compiler_class.object_extension

    def __getstate__(self):
        return self.id

    def __setstate__(self, state):
        from . import get
        tc = get(state)
        self.__dict__.update(tc.__dict__)

    def details(self):
        return f'''- cc: {self.cc}
- cxx: {self.cxx}
- link: {self.link}
- as: {self.as_}
- nm: {self.nm}
- ar: {self.ar}
- strip: {self.strip}
- dbg: {self.dbg}
'''

    def __repr__(self):
        return f'{self.name}\n{self.details()}'


def _find_compiler_tool(tool_names, cc_path, compiler_name, version, tools_prefix=None):
    if isinstance(tool_names, str):
        tool_names = {tool_names}
    for tool in tool_names:
        path_list = [cc_path.with_name(f'{compiler_name}-{tool}-{version.major}'),
                     cc_path.parent / f'{tool}-{version.major}']
        if tools_prefix:
            path_list.insert(0, cc_path.with_name(f'{tools_prefix}-{tool}-{version.major}'))
        for path in path_list:
            if path.exists():
                return path
        tool_path = shutil.which(tool)
        if tool_path and Path(tool_path).exists():
            return tool_path


class UnixToolchain(Toolchain):

    def __init__(self, name, version, arch, cc_path, cxx_path, debugger, tools_prefix, **kwargs):
        from cpppm.build.compiler import UnixCompiler

        gold = _find_compiler_tool('gold', cc_path, name, version, tools_prefix)
        if gold:
            if 'link_flags' not in kwargs:
                kwargs['link_flags'] = []
            kwargs['link_flags'].append('-fuse-ld=gold')

        super().__init__(name, version, arch, cc_path, cxx_path,
                         as_=cc_path,
                         nm=_find_compiler_tool('nm', cc_path, name, version, tools_prefix),
                         ar=_find_compiler_tool('ar', cc_path, name, version, tools_prefix),
                         link=cxx_path,
                         strip=_find_compiler_tool('strip', cc_path, name, version, tools_prefix),
                         dbg=_find_compiler_tool(debugger, cc_path, name, version, tools_prefix),
                         compiler_class=UnixCompiler, **kwargs)

def _get_unix_compiler_version(compiler_path):
    compiler_path = Path(compiler_path)
    import subprocess as sp
    proc = sp.Popen([compiler_path, '--version'], stdout=sp.PIPE, stderr=sp.STDOUT, universal_newlines=True)
    out, _ = proc.communicate()
    for line in out.splitlines():
        m = re.search(r'\s+(\d+)\.(\d+)\.(\d+)', line, re.IGNORECASE)
        if m:
            return Version(major=int(m.group(1)), minor=int(m.group(2)), patch=int(m.group(3)))


def find_unix_toolchains(cc_name, cxx_name, debugger, archs=None, version=None, tools_prefix=None, **kwargs):
    toolchains = list()
    if archs is None:
        archs = [detect.build_arch()]
    for arch in archs:
        for cc_path in find_executables(rf'{cc_name}($|-\d+$)', regex=True):
            compiler_version = _get_unix_compiler_version(cc_path)
            if version and not SimpleSpec(version).match(compiler_version):
                continue
            cxx_path = cc_path.parent / cc_path.name.replace(cc_name, cxx_name)
            if not cxx_path.exists():
                logging.warning(f'Cannot find cxx path for {cxx_name} (should be: "{cxx_path}")')
                continue
            toolchain = UnixToolchain(cc_name, compiler_version, arch, cc_path, cxx_path, debugger, tools_prefix, **kwargs)
            if arch == 'x86_64':
                toolchain.cxx_flags.append('-m64')
                toolchain.c_flags.append('-m64')
            else:
                toolchain.cxx_flags.append('-m32')
                toolchain.c_flags.append('-m32')
            toolchains.append(toolchain)
    return toolchains

import logging
import re
import shutil
from abc import abstractmethod
from pathlib import Path

from conans.client.conf.compiler_id import detect_compiler_id
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
    def __init__(self, name, compiler_id, arch, cc, cxx, as_, ar, link, nm=None, ex=None, strip=None, dbg=None,
                 libcxx=None, c_flags=None, cxx_flags=None, link_flags=None, compiler_class=None, env=None):
        self.name = name
        self.compiler_id = compiler_id
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
            if self.compiler_id.name == 'clang':
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
        return self.compiler_id.major

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
        profile_args = [f'compiler={self.compiler_id.name}',
                        f'compiler.version={self.conan_version}',
                        f'build_type={self._build_type}',
                        f'arch_build={self.arch}']
        if self.libcxx:
            profile_args.append(f'compiler.libcxx={self.libcxx}{self.libcxx_abi_version}')
        self.conan_profile = profile_from_args(None,
                                               profile_args,
                                               None, self.env_list, None, app.cache)
        self.conan_settings = self.conan_profile.settings

    @property
    def version(self):
        return self.compiler_id.version

    @property
    def major(self):
        return self.compiler_id.major

    @property
    def id(self):
        return f'{self.name}-{self.conan_version}-{self.arch}'

    @property
    def cxx_compiler(self):
        return self.compiler_class(self)

    def __cache_save__(self):
        return self.id

    @classmethod
    def __cache_load__(cls, id_):
        from . import get
        return get(id_)

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


def _find_compiler_tool(tool_names, cc_path, compiler_id, tools_prefix=None):
    if isinstance(tool_names, str):
        tool_names = {tool_names}
    for tool in tool_names:
        path_list = [cc_path.with_name(f'{compiler_id.name}-{tool}-{compiler_id.major}'),
                     cc_path.parent / f'{tool}-{compiler_id.major}']
        if tools_prefix:
            path_list.insert(0, cc_path.with_name(f'{tools_prefix}-{tool}-{compiler_id.major}'))
        for path in path_list:
            if path.exists():
                return path
        tool_path = shutil.which(tool)
        if tool_path and Path(tool_path).exists():
            return tool_path


class UnixToolchain(Toolchain):

    def __init__(self, compiler_id, arch, cc_path, cxx_path, debugger, tools_prefix, **kwargs):
        from cpppm.build.compiler import UnixCompiler

        gold = _find_compiler_tool('gold', cc_path, compiler_id, tools_prefix)
        if gold:
            if 'link_flags' not in kwargs:
                kwargs['link_flags'] = []
            kwargs['link_flags'].append('-fuse-ld=gold')

        super().__init__(compiler_id.name, compiler_id, arch, cc_path, cxx_path,
                         as_=cc_path,
                         nm=_find_compiler_tool('nm', cc_path, compiler_id, tools_prefix),
                         ar=_find_compiler_tool('ar', cc_path, compiler_id, tools_prefix),
                         link=cxx_path,
                         strip=_find_compiler_tool('strip', cc_path, compiler_id, tools_prefix),
                         dbg=_find_compiler_tool(debugger, cc_path, compiler_id, tools_prefix),
                         compiler_class=UnixCompiler, **kwargs)


def find_unix_toolchains(cc_name, cxx_name, debugger, archs=None, version=None, tools_prefix=None, **kwargs):
    toolchains = set()
    if archs is None:
        archs = [detect.build_arch()]
    for arch in archs:
        for cc_path in find_executables(rf'{cc_name}($|-\d+$)', regex=True):
            compiler_id = detect_compiler_id(cc_path)
            if version and not SimpleSpec(version).match(Version(compiler_id.version)):
                continue
            cxx_path = cc_path.parent / cc_path.name.replace(cc_name, cxx_name)
            if not cxx_path.exists():
                logging.warning(f'Cannot find cxx path for {cxx_name} (should be: "{cxx_path}")')
                continue
            toolchain = UnixToolchain(compiler_id, arch, cc_path, cxx_path, debugger, tools_prefix, **kwargs)
            if arch == 'x86_64':
                toolchain.cxx_flags.append('-m64')
                toolchain.c_flags.append('-m64')
            else:
                toolchain.cxx_flags.append('-m32')
                toolchain.c_flags.append('-m32')
            toolchains.add(toolchain)
    return toolchains

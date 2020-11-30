import logging
import re
import shutil
from pathlib import Path

from conans.client.conf.compiler_id import detect_compiler_id
from semantic_version import SimpleSpec, Version

from cpppm import detect
from cpppm.detect import find_executables


class ToolchainId:
    expr = re.compile(r'(?P<name>\w+)-(?P<version>[\d\.]+)-(?P<arch>[\w\d]+)')

    def __init__(self, id_):
        m = ToolchainId.expr.match(id_)
        if not m:
            raise RuntimeError(f'Invalid toolchain id: {id_} (must match regex "{ToolchainId.expr!r}")')
        self.name = m.group('name')
        self.version = m.group('version')
        self.arch = m.group('arch')


class Toolchain:
    def __init__(self, name, compiler_id, arch, cc, cxx, as_, ar, ld, nm=None, ex=None, strip=None, dbg=None,
                 libcxx=None):
        self.name = name
        self.compiler_id = compiler_id
        self.arch = arch
        self.cc = cc
        self.cxx = cxx
        self.as_ = as_
        self.nm = nm
        self.ar = ar
        self.ld = ld
        self.ex = ex
        self.strip = strip
        self.dbg = dbg
        self.libcxx = libcxx
        self.env = {
            'CC': str(self.cc),
            'CXX': str(self.cxx),
            'LD': str(self.ld)
        }
        self.env_list = []
        for k, v in self.env.items():
            self.env_list.append(f'{k}={v}')

        from cpppm import get_conan
        from conans.client.profile_loader import profile_from_args
        app = get_conan().app
        profile_args = [f'compiler={self.name}',
                        f'compiler.version={self.conan_version}']
        if self.libcxx:
            profile_args.append(f'compiler.libcxx={self.libcxx}')
        self.conan_profile = profile_from_args(None,
                                               profile_args,
                                               None, self.env_list, None, app.cache)
        self.conan_settings = self.conan_profile.settings

    @property
    def conan_version(self):
        if self.compiler_id.minor == 0:
            return self.compiler_id.major
        else:
            return self.compiler_id.major_minor

    @property
    def version(self):
        return self.compiler_id.version

    @property
    def major(self):
        return self.compiler_id.major

    @property
    def id(self):
        return f'{self.name}-{self.conan_version}-{self.arch}'

    def __cache_save__(self):
        return self.id

    def __str__(self):
        return f'''{self.id}
- cc: {self.cc}
- cxx: {self.cxx}
- as: {self.as_}
- nm: {self.nm}
- ld: {self.ld}
- ar: {self.ar}
- strip: {self.strip}
- dbg: {self.dbg}
'''


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
    def __init__(self, compiler_id, arch, cc_path, cxx_path, debugger, tools_prefix):
        super().__init__(compiler_id.name, compiler_id, arch, cc_path, cxx_path,
                         as_=cc_path,
                         nm=_find_compiler_tool('nm', cc_path, compiler_id, tools_prefix),
                         ar=_find_compiler_tool('ar', cc_path, compiler_id, tools_prefix),
                         ld=_find_compiler_tool(['gold', 'ld'], cc_path, compiler_id, tools_prefix),
                         strip=_find_compiler_tool('strip', cc_path, compiler_id, tools_prefix),
                         dbg=_find_compiler_tool(debugger, cc_path, compiler_id, tools_prefix))


def find_unix_toolchains(cc_name, cxx_name, debugger, archs=None, version=None, tools_prefix=None):
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
            toolchains.add(UnixToolchain(compiler_id, arch, cc_path, cxx_path, debugger, tools_prefix))
    return toolchains

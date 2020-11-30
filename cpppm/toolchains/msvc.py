import copy
import json
import os
import tempfile
from pathlib import Path

from conans.tools import vswhere

from conans.client.conf.compiler_id import detect_compiler_id
from semantic_version import SimpleSpec, Version

from cpppm import cache
from cpppm.detect import find_executables

import subprocess as sp

from cpppm.toolchains.toolchain import Toolchain


class VisualStudioToolchain:
    def __init__(self):
        pass


def _gen_msvc_cache(archs):
    vcvars = {
        "path": None,
        "lib": None,
        "libpath": None,
        "include": None,
        "DevEnvdir": None,
        "VSInstallDir": None,
        "VCInstallDir": None,
        "WindowsSdkDir": None,
        "WindowsLibPath": None,
        "WindowsSDKVersion": None,
        "WindowsSdkBinPath": None,
        "UniversalCRTSdkDir": None,
        "UCRTVersion": None
    }
    install_paths = [vs_install['installationPath'] for vs_install in vswhere()]
    cache_data = dict()
    for vcvarsall in find_executables('vcvarsall.bat', install_paths):
        for arch in archs:
            script = tempfile.NamedTemporaryFile(suffix='.bat', delete=False)
            tmp_dir = Path(script.name).parent
            content = f'call "{vcvarsall}" {arch}\r\n'
            for index, var in enumerate(vars):
                content += f'echo {var}=%{var}% {">" if index == 0 else ">>"} {tmp_dir}/cpppm-vcvars-{arch}.dat\r\n'
            script.write(content.encode())
            script.close()
            p = sp.Popen(['cmd', '/nologo', '/q', '/c', Path(script.name)], cwd=tmp_dir, stdout=sp.PIPE, stderr=sp.PIPE)
            _, err = p.communicate()
            if p.returncode:
                raise sp.CalledProcessError(p.returncode, err)
            with open(tmp_dir / f'cpppm-vcvars-{arch}.dat') as data:
                for line in data.readlines():
                    k, v = line.split('=')[:2]
                    vcvars[k] = v.strip()
            cache_data[arch] = copy.deepcopy(vcvars)
    return cache_data


def find_msvc_toolchains(version=None, archs=None, **kwargs):
    archs = archs or ['x86', 'x64']
    toolchains = set()
    cache_ = cache.build_root / 'cpppm-msvc-toolchains.cache'
    if not cache_.exists():
        data = _gen_msvc_cache(archs)
        json.dump(data, open(cache_, 'w'))
    else:
        data = json.load(open(cache_, 'r'))

    for arch in archs:
        vcvars = data[arch]
        paths = [p for p in vcvars['path'].split(';') if p.startswith(vcvars['VCInstallDir'])]

        for cl in find_executables('cl.exe', paths):
            link = cl.parent / 'link.exe'
            as_ = cl.parent / f'ml{"64" if arch == "x64" else ""}.exe'
            ex = cl.parent / 'lib.exe'

            here = os.getcwd()
            os.chdir(tempfile.gettempdir())
            compiler_id = detect_compiler_id(f'"{cl}"')
            os.chdir(here)

            if version and not SimpleSpec(version).match(Version(compiler_id.version)):
                continue

            from cpppm.build.compiler import MsvcCompiler
            toolchains.add(Toolchain('msvc', compiler_id, arch, cl, cl,
                                     as_=as_,
                                     ar=ex,
                                     link=link,
                                     dbg=None,
                                     cxx_flags=['/EHsc'],
                                     compiler_class=MsvcCompiler))
    return toolchains

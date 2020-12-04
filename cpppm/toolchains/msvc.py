import copy
import json
import logging
import os
import sys
import re
import tempfile
from pathlib import Path

from conans.tools import vswhere

from conans.client.conf.compiler_id import detect_compiler_id, CompilerId
from semantic_version import SimpleSpec, Version

from cpppm import cache
from cpppm.detect import find_executables

import subprocess as sp

from cpppm.toolchains.toolchain import Toolchain


class VisualStudioToolchain:
    def __init__(self):
        pass


def _get_vc_arch(arch):
    m = re.match(r'x86_([\d]{2})', arch)
    if m:
        if m.group(1) == '32':
            return f'x86'
        else:
            return f'x64'
    else:
        return arch

def _get_cl_version(cl):
    import subprocess as sp
    from conans.client.conf.compiler_id import MSVC_TO_VS_VERSION, MSVC
    out = sp.check_output(cl, stderr=sp.STDOUT, universal_newlines=True)
    for line in out.splitlines():
        m = re.search(r'version\D+(\d+)\.(\d+)\.(\d+)', line, re.IGNORECASE)
        if m:
            version = int(f'{m.group(1)}{int(m.group(2)):02}')
            if not version in MSVC_TO_VS_VERSION.keys():
                extra_versions = {
                    1928: (16, 8),
                }
                vs_version = extra_versions[version]
            else:
                vs_version = MSVC_TO_VS_VERSION[version]
            return CompilerId(MSVC, vs_version[0], vs_version[1], None)

def _gen_msvc_cache(archs):
    from cpppm import _logger
    logger = _logger.getChild('msvc-cache')
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
            vc_arch = _get_vc_arch(arch)

            script = tempfile.NamedTemporaryFile(suffix='.bat', delete=False)
            tmp_dir = Path(script.name).parent
            content = f'call "{vcvarsall}" {vc_arch}\r\n'
            for index, var in enumerate(vcvars.keys()):
                content += f'echo {var}=%{var}% {">" if index == 0 else ">>"} {tmp_dir}/cpppm-vcvars-{arch}.dat\r\n'
            script.write(content.encode())
            script.close()
            p = sp.Popen(['cmd', '/nologo', '/q', '/c', Path(script.name)], cwd=tmp_dir, stdout=sp.PIPE, stderr=sp.PIPE)
            _, err = p.communicate()
            if p.returncode:
                raise sp.CalledProcessError(p.returncode, err)
            valid = True
            with open(tmp_dir / f'cpppm-vcvars-{arch}.dat') as data:
                for line in data.readlines():
                    k, v = line.split('=')[:2]
                    v = v.strip()
                    if not v:
                        logger.debug(f'Cannot find vc variable: "{k}"')
                        # valid = False
                    vcvars[k] = v
            if valid:
                paths = [p for p in vcvars['path'].split(';') if p.startswith(vcvars['VCInstallDir'])]
                cl = find_executables('cl.exe', paths).pop()
                if cl:
                    compiler_id = _get_cl_version(cl)
                    if not compiler_id:
                        raise RuntimeError(f'Cannot detect msvc version of {cl}')
                    vcvars["cl"] = str(cl.absolute())
                    vcvars["compiler_id.name"] = compiler_id.name
                    vcvars["compiler_id.major"] = str(compiler_id.major)
                    vcvars["compiler_id.minor"] = str(compiler_id.minor)
                    vcvars["compiler_id.patch"] = str(compiler_id.patch or 0)

                    cache_data[vc_arch] = copy.deepcopy(vcvars)
                    logger.debug(f'Found msvc toolchain')

    return cache_data


def find_msvc_toolchains(version=None, archs=None, **kwargs):
    archs = archs or ['x86_64', 'x86']
    toolchains = set()
    cache_ = cache.build_root / 'cpppm-msvc-toolchains.cache'
    if not cache_.exists():
        cache.build_root.mkdir(exist_ok=True, parents=True)
        data = _gen_msvc_cache(archs)
        json.dump(data, open(cache_, 'w'))
    else:
        data = json.load(open(cache_, 'r'))

    for arch in archs:
        vc_arch = _get_vc_arch(arch)
        if vc_arch not in data:
            data.update(_gen_msvc_cache([vc_arch]))
            json.dump(data, open(cache_, 'w'))

        if vc_arch not in data:
            continue

        vcvars = data[vc_arch]

        cl = Path(vcvars["cl"])
        compiler_id = CompilerId(vcvars["compiler_id.name"],
                                 int(vcvars["compiler_id.major"]), int(vcvars["compiler_id.minor"]),
                                 int(vcvars["compiler_id.patch"]))

        if version and not SimpleSpec(version).match(Version(compiler_id.version)):
            continue

        link = cl.parent / 'link.exe'
        as_ = cl.parent / f'ml{"64" if vc_arch == "x64" else ""}.exe'
        ar = cl.parent / 'lib.exe'
        from cpppm.build.compiler import MsvcCompiler
        toolchains.add(Toolchain('msvc', compiler_id, arch, cl, cl,
                                 as_=as_,
                                 ar=ar,
                                 link=link,
                                 dbg=None,
                                 cxx_flags=['/EHsc'],
                                 compiler_class=MsvcCompiler,
                                 env=vcvars))

    return toolchains

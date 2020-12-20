import copy
import re
import tempfile
from pathlib import Path
from typing import List, Dict

from conans.tools import vswhere

from semantic_version import SimpleSpec, Version

from cpppm import cache
from cpppm.cache import CacheRoot, CacheAttr
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


MSVC_TO_VS_VERSION = {800: (1, 0),
                      900: (2, 0),
                      1000: (4, 0),
                      1010: (4, 1),
                      1020: (4, 2),
                      1100: (5, 0),
                      1200: (6, 0),
                      1300: (7, 0),
                      1310: (7, 1),
                      1400: (8, 0),
                      1500: (9, 0),
                      1600: (10, 0),
                      1700: (11, 0),
                      1800: (12, 0),
                      1900: (14, 0),
                      1910: (15, 0),
                      1911: (15, 3),
                      1912: (15, 5),
                      1913: (15, 6),
                      1914: (15, 7),
                      1915: (15, 8),
                      1916: (15, 9),
                      1920: (16, 0),
                      1921: (16, 1),
                      1922: (16, 2),
                      1923: (16, 3),
                      1924: (16, 4),
                      1925: (16, 5),
                      1926: (16, 6),
                      1927: (16, 7),
                      1928: (16, 8),
                      }


def _get_cl_version(cl):
    import subprocess as sp
    proc = sp.Popen(cl, stdout=sp.PIPE, stderr=sp.STDOUT, universal_newlines=True)
    out, _ = proc.communicate()
    for line in out.splitlines():
        m = re.search(r'version\D+(\d+)\.(\d+)\.(\d+)', line, re.IGNORECASE)
        if m:
            version = int(f'{m.group(1)}{int(m.group(2)):02}')
            vs_version = MSVC_TO_VS_VERSION[version]
            return 'Visual Studio', str(vs_version[0]), Version(major=vs_version[0], minor=vs_version[1], patch=0)


class MSVCCache(CacheRoot):
    vcvars_script_paths: List = CacheAttr(list())
    data: Dict = CacheAttr(dict())

    def __init__(self):
        super().__init__(cache.build_root / 'cpppm-msvc-toolchains.cache')


__msvc_cache = None


def get_msvc_cache(archs):
    global __msvc_cache
    from cpppm import _logger
    logger = _logger.getChild('msvc-cache')
    if __msvc_cache is None:
        __msvc_cache = MSVCCache()
    msvc_cache = __msvc_cache
    if len(msvc_cache.vcvars_script_paths) == 0:
        install_paths = [vs_install['installationPath'] for vs_install in vswhere()]
        msvc_cache.vcvars_script_paths = list(find_executables('vcvarsall.bat', install_paths))

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
    for vcvarsall in msvc_cache.vcvars_script_paths:
        for arch in archs:
            vc_arch = _get_vc_arch(arch)
            if arch not in msvc_cache.data.keys():
                script = tempfile.NamedTemporaryFile(suffix='.bat', delete=False)
                tmp_dir = Path(script.name).parent
                content = f'call "{vcvarsall}" {vc_arch}\r\n'
                for index, var in enumerate(vcvars.keys()):
                    content += f'echo {var}=%{var}% {">" if index == 0 else ">>"} {tmp_dir}/cpppm-vcvars-{arch}.dat\r\n'
                script.write(content.encode())
                script.close()
                p = sp.Popen(['cmd', '/nologo', '/q', '/c', Path(script.name)], cwd=tmp_dir, stdout=sp.PIPE,
                             stderr=sp.PIPE)
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
                        compiler, version_str, version = _get_cl_version(cl)
                        if not compiler:
                            raise RuntimeError(f'Cannot detect msvc version of {cl}')
                        vcvars["cl"] = str(cl.absolute())
                        vcvars["compiler_id.name"] = compiler
                        vcvars["compiler_id.version"] = version_str
                        vcvars["compiler_id.major"] = str(version.major)
                        vcvars["compiler_id.minor"] = str(version.minor)
                        vcvars["compiler_id.patch"] = str(version.patch or 0)

                        msvc_cache.data[arch] = copy.deepcopy(vcvars)
                        logger.debug(f'Found msvc toolchain {compiler}-{version}')

    msvc_cache.cache_save()
    return msvc_cache


def find_msvc_toolchains(version=None, archs=None, **kwargs):
    archs = archs or ['x86_64', 'x86']
    toolchains = list()
    msvc_cache = get_msvc_cache(archs)

    for arch in archs:
        if arch not in msvc_cache.data:
            raise RuntimeError(f'Cannot find toolchain for {arch} architecture')

        vcvars = msvc_cache.data[arch]

        cl = Path(vcvars["cl"])
        compiler = vcvars["compiler_id.name"]
        version = Version(major=int(vcvars["compiler_id.major"]), minor=int(vcvars["compiler_id.minor"]),
                          patch=int(vcvars["compiler_id.patch"]))

        if version and not SimpleSpec(vcvars["compiler_id.version"]).match(version):
            continue

        link = cl.parent / 'link.exe'
        as_ = cl.parent / f'ml{"64" if arch == "x86_64" else ""}.exe'
        ar = cl.parent / 'lib.exe'
        from cpppm.build.compiler import MsvcCompiler
        toolchains.append(Toolchain(compiler, version, arch, cl, cl,
                                    as_=as_,
                                    ar=ar,
                                    link=link,
                                    dbg=None,
                                    cxx_flags=['/EHsc'],
                                    compiler_class=MsvcCompiler,
                                    env=vcvars))

    return toolchains

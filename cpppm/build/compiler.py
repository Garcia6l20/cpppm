import asyncio
import hashlib
import re
import shutil
from pathlib import Path
from typing import Union

from cpppm import _get_logger
from cpppm.config import config
from cpppm.utils.runner import Runner, ProcessError


class CompileError(ProcessError):
    pass


class Compiler(Runner):
    force = False
    _include_pattern = re.compile(r'#include [<"](.+)[>"]')

    def __init__(self, exe, ccache, *args, **kwargs):
        self.commands = list()
        if ccache:
            super().__init__(ccache, args={exe}, recorder=self.on_cmd, **kwargs)
            self._logger = _get_logger(self, Path(exe).name)
            self._logger.info('using ccache')
        else:
            super().__init__(exe, recorder=self.on_cmd, **kwargs)
            self._logger = _get_logger(self, Path(exe).name)

    def on_cmd(self, cmd):
        self.commands.append(cmd)

    def is_clang(self):
        return config._conan_compiler[0] in {'clang', 'apple-clang'}

    def source_deps(self, target, source):
        deps = set()
        for line in open(source.absolute(), 'r'):
            for m in re.finditer(Compiler._include_pattern, line):
                include = m.group(1)
                for p in target.include_dirs:
                    fullpath = (p / include)
                    if fullpath.exists():
                        deps.add(fullpath)
        return deps

    def _is_source_outdated(self, target, source, deps):
        for dep in deps:
            sha = hashlib.sha1(str(dep).encode())
            sha.update(str(source.absolute()).encode())
            timestamp = target.build_path / 'deps' / (sha.hexdigest() + '.ts')
            if not timestamp.exists() or timestamp.stat().st_mtime < dep.stat().st_mtime:
                self._logger.debug(f"outdated: {source} (changed: {dep})")
                return True
        return False

    def _update_deps_timestamps(self, target, source, deps):
        for dep in deps:
            sha = hashlib.sha1(str(dep).encode())
            sha.update(str(source.absolute()).encode())
            timestamp = target.build_path / 'deps' / (sha.hexdigest() + '.ts')
            timestamp.parent.mkdir(exist_ok=True, parents=True)
            timestamp.touch(exist_ok=True)

    async def compile(self, target: 'cpppm.target.Target', pic=True,
                force=False):
        if target._built is not None:
            return target._built

        force = force or Compiler.force
        self._logger.info(f'building {target}')
        output = target.build_path.absolute()
        opts = {'-c'}
        if self.is_clang() == 'clang':
            opts.add(f'-stdlib={config.libcxx}')
        if pic:
            opts.add('-fPIC')

        opts.update({f'-I{str(path)}' for path in target.include_dirs.absolute()})

        for k, v in target.compile_definitions.items():
            if v is not None:
                opts.add(f'-D{k}={v}')
            else:
                opts.add(f'-D{k}')

        opts.update(target.compile_options)
        objs = set()
        compilations = set()
        for source in target.compile_sources.absolute():
            out = output / source.with_suffix('.o').name
            objs.add(out)
            source_deps = self.source_deps(target, source)
            if force or not out.exists() or (source.lstat().st_mtime > out.lstat().st_mtime) \
                    or (self._is_source_outdated(target, source, source_deps)):

                async def do_compile():
                    self._logger.info(f'compiling {out.name} ({target})')
                    await self.run(*opts, str(source), '-o', str(out))
                    self._update_deps_timestamps(target, source, source_deps)
                compilations.add(do_compile())
            else:
                self._logger.info(f'object {out} is up-to-date')

        try:
            await asyncio.gather(*compilations)
        except ProcessError as err:
            raise CompileError(err)

        if len(objs):
            opts = set()
            if pic:
                opts.add('-fPIC')
            output = target.bin_path.absolute()
            output.parent.mkdir(exist_ok=True, parents=True)
            opts.update({f'-L{str(d.absolute())}' for d in target.library_dirs})
            for lib in target._all_libraries():
                if isinstance(lib, str):
                    opts.add(f'-l{lib}')
                elif not lib.is_header_only:
                    # opts.add(f'-l{":" if "." in lib.bin_path.suffix else ""}{str(lib.bin_path.name)}')
                    opts.add(f'-l{lib.name}')
            try:
                if str(output).endswith('.so'):
                    # shared library
                    self._logger.info(f'creating library {output.name}')
                    await self.run('-shared', *opts, *[str(o) for o in objs], '-o', str(output))
                elif str(output).endswith('.a'):
                    # archive
                    self._logger.info(f'creating archive {output.name}')
                    exe = Runner(shutil.which('ar'), recorder=self.on_cmd)
                    await exe.run('rcs', str(output), *[str(o) for o in objs])
                else:
                    # executable
                    self._logger.info(f'linking {output.name}')
                    await self.run(*[str(o) for o in objs], *opts, '-o', str(output))
            except ProcessError as err:
                raise CompileError(err)

        target._built = len(compilations)
        return target._built


def get_compiler(name: Union[str, Path] = None):
    ccache = shutil.which('ccache')

    if not name:
        cc = config.cxx
        exe = shutil.which(cc)
    else:
        cc = Path(name)
        if cc.is_absolute():
            exe = cc
        else:
            exe = shutil.which(str(cc))
    return Compiler(exe, ccache)

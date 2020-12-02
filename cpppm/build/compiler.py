import asyncio
import hashlib
import re
import shutil
from abc import abstractmethod

from cpppm import _get_logger
from cpppm.config import config
from cpppm.utils.runner import Runner, ProcessError


class CompileError(ProcessError):
    pass


class Compiler:
    force = False
    _include_pattern = re.compile(r'#include [<"](.+)[>"]')

    def __init__(self, toolchain, *args, **kwargs):

        assert hasattr(self, 'object_extension')
        assert hasattr(self, 'static_extension')
        assert hasattr(self, 'shared_extension')
        assert hasattr(self, 'include_path_flag')
        assert hasattr(self, 'lib_path_flag')
        assert hasattr(self, 'lib_flag')
        assert hasattr(self, 'define_flag')

        self.commands = list()
        ccache = shutil.which('ccache') if config.ccache else None
        self.toolchain = toolchain
        self._logger = _get_logger(self, toolchain.id)
        if ccache:
            self.cc_runner = Runner(ccache, args={str(toolchain.cc), *args}, recorder=self.on_cmd, **kwargs)
            self.cxx_runner = Runner(ccache, args={str(toolchain.cxx), *args}, recorder=self.on_cmd, **kwargs)
            self.ar_runner = Runner(ccache, args={str(toolchain.ar), *args}, recorder=self.on_cmd, **kwargs)
            self.link_runner = Runner(ccache, args={str(toolchain.link), *args}, recorder=self.on_cmd, **kwargs)
            self._logger.info('using ccache')
        else:
            self.cc_runner = Runner(toolchain.cc, args=args, recorder=self.on_cmd, **kwargs)
            self.cxx_runner = Runner(toolchain.cxx, args=args, recorder=self.on_cmd, **kwargs)
            self.ar_runner = Runner(toolchain.ar, args=args, recorder=self.on_cmd, **kwargs)
            self.link_runner = Runner(toolchain.link, args=args, recorder=self.on_cmd, **kwargs)

    def on_cmd(self, cmd):
        self.commands.append(cmd)

    def is_clang(self):
        return self.toolchain.name in {'clang', 'apple-clang'}

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

    @abstractmethod
    async def compile_object(self, source, output_path, flags=None, pic=False, test=False):
        pass

    @abstractmethod
    async def create_static_lib(self, output, objs, flags=None):
        pass

    @abstractmethod
    async def create_shared_lib(self, output, objs, flags=None, pic=False):
        pass

    @abstractmethod
    async def link_executable(self, output, objs, flags=None, pic=False):
        pass

    async def compile(self, target: 'cpppm.target.Target', pic=True,
                      force=False):
        force = force or Compiler.force
        self._logger.info(f'building {target}')
        output = target.build_path.absolute()
        opts = set()

        opts.update({f'{self.include_path_flag}{str(path)}' for path in target.include_dirs.absolute()})

        for k, v in target.compile_definitions.items():
            if v is not None:
                opts.add(f'{self.define_flag}{k}={v}')
            else:
                opts.add(f'{self.define_flag}{k}')

        opts.update(target.compile_options)
        objs = set()
        compilations = set()
        for source in target.compile_sources.absolute():
            out = output / source.with_suffix(self.object_extension).name
            objs.add(out)
            source_deps = self.source_deps(target, source)
            if force or not out.exists() or (source.lstat().st_mtime > out.lstat().st_mtime) \
                    or (self._is_source_outdated(target, source, source_deps)):

                async def do_compile():
                    self._logger.info(f'compiling {out.name} ({target})')
                    await self.compile_object(source, output, opts, pic=pic)
                    self._update_deps_timestamps(target, source, source_deps)

                compilations.add(do_compile())
            else:
                self._logger.info(f'object {out} is up-to-date')

        try:
            await asyncio.gather(*compilations)
        except ProcessError as err:
            raise CompileError(err)

        if len(compilations):
            opts = {*self.toolchain.link_flags}
            output = target.bin_path.absolute()
            output.parent.mkdir(exist_ok=True, parents=True)
            opts.update({f'{self.lib_path_flag}{str(d.absolute())}' for d in target.library_dirs})
            for lib in target.lib_dependencies:
                if isinstance(lib, str):
                    opts.add(f'{self.lib_flag}{lib}')
                elif not lib.is_header_only:
                    opts.add(f'{self.lib_flag}{lib.name}')
            try:
                if str(output).endswith(self.shared_extension):
                    # shared library
                    self._logger.info(f'creating library {output.name}')
                    await self.create_shared_lib(output, [str(o) for o in objs], list(opts), pic=pic)
                elif str(output).endswith(self.static_extension):
                    # archive
                    self._logger.info(f'creating archive {output.name}')
                    await self.create_static_lib(str(output), [str(o) for o in objs], None)
                else:
                    # executable
                    self._logger.info(f'linking {output.name}')
                    if self.is_clang():
                        opts.add(f'-stdlib={config.toolchain.libcxx}')
                    await self.link_executable(str(output), [str(o) for o in objs], list(opts), pic=pic)
            except ProcessError as err:
                raise CompileError(err)

        target._built = len(compilations)
        return target._built


class UnixCompiler(Compiler):

    def __init__(self, toolchain, *args, **kwargs):
        self.object_extension = '.o'
        self.static_extension = '.a'
        self.shared_extension = '.so'
        self.include_path_flag = '-I'
        self.lib_path_flag = '-L'
        self.lib_flag = '-l'
        self.define_flag = '-D'
        super().__init__(toolchain, *args, **kwargs)

    async def compile_object(self, source, output_path, flags=None, test=False, pic=False):
        opts = self.toolchain.cxx_flags
        if pic:
            opts.append('-fPIC')
        if flags:
            opts.extend(flags)
        out = output_path / source.with_suffix('.o').name
        return await self.cxx_runner.run(*opts, '-c', str(source), '-o', str(out), always_return=test)

    async def create_static_lib(self, output, objs, flags=None):
        await self.ar_runner.run('rcs', str(output), objs)

    async def create_shared_lib(self, output, objs, flags=None, pic=False):
        flags = flags or []
        if pic:
            flags.append('-fPIC')
        await self.link_runner.run('-shared', *flags, *objs, '-o', str(output))

    async def link_executable(self, output, objs, flags=None, pic=False):
        flags = flags or []
        if pic:
            flags.append('-fPIC')
        await self.link_runner.run(*objs, *flags, '-o', str(output))


class MsvcCompiler(Compiler):

    def __init__(self, toolchain, *args, **kwargs):
        self.object_extension = '.obj'
        self.static_extension = '.lib'
        self.shared_extension = '.dll'
        self.include_path_flag = '/I'
        self.lib_path_flag = '/LIBPATH:'
        self.lib_flag = '/LIB'
        self.define_flag = '/D'
        super().__init__(toolchain, *args, **kwargs)

    async def compile_object(self, source, output_path, flags=None, test=False, pic=False):
        opts = self.toolchain.cxx_flags
        if flags:
            opts.extend(flags)
        out = output_path / source.with_suffix(self.object_extension).name
        return await self.cxx_runner.run(*opts, '/c', str(source), str(out), always_return=test)

    async def create_static_lib(self, output, objs, flags=None):
        await self.ar_runner.run(*objs, str(output))

    async def create_shared_lib(self, output, objs, flags=None, pic=False):
        flags = flags or []
        await self.link_runner.run('/DLL', *flags, *objs, f'/OUT:{str(output)}')

    async def link_executable(self, output, objs, flags=None, pic=False):
        flags = flags or []
        await self.link_runner.run(*flags, *objs, f'/OUT:{str(output)}')

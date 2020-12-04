import asyncio
import hashlib
import re
import shutil
from abc import abstractmethod

import platform

from cpppm import _get_logger
from cpppm.config import config
from cpppm.utils.pathlist import PathList
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
            self.cxx_runner = Runner(toolchain.cxx, args=args, recorder=self.on_cmd, **kwargs) if toolchain.cc != toolchain.cxx else self.cc_runner
            self.ar_runner = Runner(toolchain.ar, args=args, recorder=self.on_cmd, **kwargs)
            self.link_runner = Runner(toolchain.link, args=args, recorder=self.on_cmd, **kwargs)

    def on_cmd(self, cmd):
        self.commands.append(cmd)

    def is_clang(self):
        return self.toolchain.name in {'clang', 'apple-clang'}

    def is_msvc(self):
        return self.toolchain.name in {'msvc'}

    def source_deps(self, target, source):
        deps = set()
        for line in open(source.absolute(), 'r'):
            for m in re.finditer(Compiler._include_pattern, line):
                include = m.group(1)
                for p in target.include_dirs.absolute():
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
    def make_include_dirs_option(self, include_dirs: PathList):
        pass

    @abstractmethod
    def make_link_dirs_option(self, include_dirs: PathList):
        pass

    @abstractmethod
    def make_link_option(self, libs):
        pass

    @abstractmethod
    async def compile_object(self, source, output_path, flags=None, pic=False, test=False):
        pass

    @abstractmethod
    async def create_static_lib(self, output, objs, flags=None):
        pass

    @abstractmethod
    async def create_shared_lib(self, output, objs, flags=None, pic=False, lib_path=None):
        pass

    @abstractmethod
    async def link_executable(self, output, objs, flags=None, pic=False):
        pass

    async def compile(self, target: 'cpppm.target.Target', pic=True,
                      force=False):
        from cpppm import Library
        force = force or Compiler.force
        self._logger.info(f'building {target}')
        output = target.build_path.absolute()
        opts = list()
        opts.extend(self.make_include_dirs_option(target.include_dirs))
        # opts.extend(self.make_compile_options(target.compile_definitions))

        if platform.system() == 'Windows' and \
                isinstance(target, Library) and \
                target.shared:
            opts.append(f'/D{target.macro_name}_DLL_EXPORT=1')

        for k, v in target.compile_definitions.items():
            if v is not None:
                opts.append(f'{self.define_flag}{k}={v}')
            else:
                opts.append(f'{self.define_flag}{k}')

        opts.extend(target.compile_options)
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
            opts = [*self.toolchain.link_flags]
            output = target.bin_path.absolute()
            output.parent.mkdir(exist_ok=True, parents=True)
            opts.extend(self.make_link_dirs_option(target.library_dirs))
            lib_names = []
            for lib in target.lib_dependencies:
                if isinstance(lib, str):
                    lib_names.append(lib)
                elif not lib.is_header_only:
                    lib_names.append(lib.name)
            opts.extend(self.make_link_option(lib_names))
            try:
                if isinstance(target, Library) and not target.is_header_only:
                    if target.shared:
                        self._logger.info(f'creating library {output.name}')
                        await self.create_shared_lib(output, objs, list(opts), pic=pic, lib_path=target.lib_path)
                    else:
                        self._logger.info(f'creating static library {output.name}')
                        await self.create_static_lib(output, objs, None)
                else:
                    # executable
                    self._logger.info(f'linking {output.name}')
                    if self.is_clang():
                        opts.append(f'-stdlib={config.toolchain.libcxx}')
                    await self.link_executable(output, objs, list(opts), pic=pic)
            except ProcessError as err:
                raise CompileError(err)

        target._built = len(compilations)
        return target._built


class UnixCompiler(Compiler):
    build_type_flags = {
        'Release': ('-O3', '-DNDEBUG'),
        'Debug': ('-g',),
        'RelWithDebInfo': ('-O2', '-g', '-DNDEBUG'),
        'MinSizeRel': ('-Os', '-DNDEBUG'),
    }
    object_extension = '.o'
    static_extension = '.a'
    shared_extension = '.so'
    include_path_flag = '-I'
    lib_path_flag = '-L'
    lib_flag = '-l'
    define_flag = '-D'

    def __init__(self, toolchain, *args, **kwargs):
        super().__init__(toolchain, *args, **kwargs)

    def make_include_dirs_option(self, include_dirs: PathList):
        return [f'-I{d}' for d in include_dirs.absolute()]

    def make_link_dirs_option(self, link_dirs: PathList):
        return [f'-L{d}' for d in link_dirs.absolute()]

    def make_link_option(self, libs):
        return [f'-l{lib}' for lib in libs]

    async def compile_object(self, source, output_path, flags=None, test=False, pic=False):
        opts = self.toolchain.cxx_flags
        if pic:
            opts.append('-fPIC')
        if flags:
            opts.extend(flags)
        out = output_path / source.with_suffix('.o').name
        return await self.cxx_runner.run(*opts, '-c', str(source), '-o', str(out), always_return=test)

    async def create_static_lib(self, output, objs, flags=None):
        await self.ar_runner.run('rcs', str(output), [str(o) for o in objs])

    async def create_shared_lib(self, output, objs, flags=None, pic=False, **kwargs):
        flags = flags or []
        if pic:
            flags.append('-fPIC')
        await self.link_runner.run('-shared', *flags, *[str(o) for o in objs], '-o', str(output))

    async def link_executable(self, output, objs, flags=None, pic=False):
        flags = flags or []
        if pic:
            flags.append('-fPIC')
        await self.link_runner.run(*[str(o) for o in objs], *flags, '-o', str(output))


class MsvcCompiler(Compiler):
    build_type_flags = {
        'Release': ['/O2', '/D NDEBUG', '/MD'],
        'Debug': ['/O0', '/G'],
    }
    object_extension = '.obj'
    static_extension = '.lib'
    shared_extension = '.dll'
    include_path_flag = '/I'
    lib_path_flag = '/LIBPATH:'
    lib_flag = '/LIB'
    define_flag = '/D'

    def make_include_dirs_option(self, include_dirs: PathList):
        return [f'/I{d.as_posix()}' for d in include_dirs.absolute()]

    def make_link_dirs_option(self, link_dirs: PathList):
        return [f'/LIBPATH:{d.as_posix()}' for d in link_dirs.absolute()]

    def make_link_option(self, libs):
        return [f'{lib}.lib' for lib in libs]

    async def compile_object(self, source, output_path, flags=None, test=False, pic=False):
        opts = self.toolchain.cxx_flags
        if flags:
            opts.extend(flags)
        out = output_path / source.with_suffix(self.object_extension).name
        return await self.cxx_runner.run('/nologo', *opts, '/c', str(source.as_posix()), f'/Fo{str(out.as_posix())}',
                                         always_return=test)

    async def create_static_lib(self, output, objs, flags=None):
        await self.ar_runner.run('/nologo', *[f'{o.as_posix()}' for o in objs], f'/OUT:{str(output.as_posix())}')

    async def create_shared_lib(self, output, objs, flags=None, lib_path=None, **kwargs):
        flags = flags or []
        await self.link_runner.run('/nologo', f'/IMPLIB:{lib_path.as_posix()}', '/dll', *flags, *[f'{o.as_posix()}' for o in objs],
                                   f'/OUT:{str(output.as_posix())}')

    async def link_executable(self, output, objs, flags=None, pic=False):
        flags = flags or []
        await self.link_runner.run('/nologo', *flags, *[f'{o.as_posix()}' for o in objs], f'/OUT:{str(output)}')

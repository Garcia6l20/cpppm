import shutil
import os
from pathlib import Path
from typing import Union, Dict

from cpppm.utils.runner import Runner, ProcessError


class CompileError(ProcessError):
    pass


class Compiler(Runner):

    force = False

    def __init__(self, *args, **kwargs):
        self.commands = list()
        super().__init__(*args, recorder=self.on_cmd, **kwargs)

    def on_cmd(self, cmd):
        self.commands.append(cmd)

    def compile(self, target: 'cpppm.target.Target', pic=True,
                force=False):
        force = force or Compiler.force
        self._logger.info(f'building {target}')
        built = False
        output = target.build_path.absolute()
        opts = {'-c'}
        if pic:
            opts.add('-fPIC')

        opts.update({f'-I{str(path)}' for path in target.include_dirs.absolute()})

        for k, v in target.compile_definitions.items():
            if v is not None:
                opts.add(f'-D{k}={v}')
            else:
                opts.add(f'-D{k}')

        opts.update(target.compile_options)
        objs = []
        for source in target.compile_sources.absolute():
            out = output / source.with_suffix('.o').name
            objs.append(out)
            if force or not out.exists() or (source.lstat().st_mtime > out.lstat().st_mtime):
                self._logger.info(f'compiling {out.name}')
                try:
                    self.run(*opts, str(source), '-o', str(out))
                    built = True
                except ProcessError as err:
                    raise CompileError(err)
            else:
                self._logger.info(f'object {out} is up-to-date')

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
                    self.run('-shared', *opts, *[str(o) for o in objs], '-o', str(output))
                elif str(output).endswith('.a'):
                    # archive
                    self._logger.info(f'creating archive {output.name}')
                    exe = Runner(shutil.which('ar'), recorder=self.on_cmd)
                    exe.run('rcs', str(output), *[str(o) for o in objs])
                else:
                    # executable
                    self._logger.info(f'linking {output.name}')
                    self.run(*[str(o) for o in objs], *opts, '-o', str(output))
            except ProcessError as err:
                raise CompileError(err)

        return built


def get_compiler(name: Union[str, Path] = None):
    if not name:
        cc = os.getenv('CC') or 'cc'
        exe = shutil.which(cc)
    else:
        cc = Path(name)
        if cc.is_absolute():
            exe = cc
        else:
            exe = shutil.which(str(cc))
    return Compiler(exe)

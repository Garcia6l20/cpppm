import shutil
import os
from pathlib import Path
from typing import Union, Dict

from cpppm.utils.runner import Runner, ProcessError


class CompileError(ProcessError):
    pass


class Compiler(Runner):

    def __init__(self, *args, **kwargs):
        self.commands = list()
        super().__init__(*args, recorder=self.on_cmd, **kwargs)

    def on_cmd(self, cmd):
        self.commands.append(cmd)

    def compile(self, sources, output, data, force=False, pic=True):
        output = Path(output)
        built = False
        assert output.is_dir()
        opts = {'-c'}
        if pic:
            opts.add('-fPIC')
        if 'include_paths' in data:
            opts.update({f'-I{str(path)}' for path in data['include_paths']})
        if 'compile_definitions' in data:
            opts.update({f'-D{definition}' for definition in data['compile_definitions']})
        if 'compile_options' in data:
            opts.update(data['compile_options'])
        objs = []
        for source in sources:
            out = output / source.with_suffix('.o').name
            objs.append(out)
            if force or not out.exists() or (source.lstat().st_mtime > out.lstat().st_mtime):
                try:
                    self.run(*opts, str(source), '-o', str(out))
                    built = True
                except ProcessError as err:
                    raise CompileError(err)
            else:
                self._logger.info(f'object {out} is up-to-date')
        return built, objs

    @staticmethod
    def _make_link_args(data: Dict):
        args = []
        if 'library_paths' in data:
            args.extend({f'-L{str(path)}' for path in data['library_paths']})
        if 'libraries' in data:
            args.extend({f'-l{":" if "." in Path(lib).suffix else ""}{str(lib)}' for lib in data['libraries']})
        return args

    def make_library(self, objects, output, data):
        output = output if isinstance(output, Path) else Path(output)
        shared = output.suffix == '.so'
        if shared:
            try:
                link_args = self._make_link_args(data)
                self.run('-shared', *link_args, *[str(o) for o in objects], '-o', str(output))
            except ProcessError as err:
                raise CompileError(err)
        else:
            try:
                exe = Runner(shutil.which('ar'), recorder=self.on_cmd)
                exe.run('rcs', str(output), *[str(o) for o in objects])
            except ProcessError as err:
                raise CompileError(err)

    def link(self, objects, output, data):
        link_args = self._make_link_args(data)
        try:
            output.parent.mkdir(parents=True, exist_ok=True)
            self.run(*[str(o) for o in objects], *link_args, '-o', str(output))
        except ProcessError as err:
            raise CompileError(err)


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

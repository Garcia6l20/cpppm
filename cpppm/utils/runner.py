import asyncio
import os
import sys
from pathlib import Path
from typing import Dict, Union

from .decorators import working_directory
from .. import _get_logger


class ProcessError(RuntimeError):
    pass


class Runner:
    def __init__(self, executable, cwd: Path = None, env=None, recorder=None, args=None):
        self._logger = _get_logger(self, executable)
        self.executable = str(executable.absolute().as_posix()) if isinstance(executable, Path) else executable
        self.cwd = cwd
        self.env = env
        self.recorder = recorder
        self.args = args or set()

    async def run(self, *args, cwd: Union[str, Path] = None, env: Dict = None, dry_run=False, recorder=None,
                  stdout=None, always_return=False):
        if not cwd:
            cwd = self.cwd or Path.cwd()
        if not env:
            env = self.env
        else:
            env.update(self.env)
        recorder = recorder or self.recorder

        @working_directory(cwd=Path(cwd), env=env)
        async def do_run():
            cmd = ' '.join([self.executable, *self.args, *args])
            self._logger.debug(f'cwd: {Path.cwd()}')
            self._logger.debug(f'cmd: {cmd}')
            if recorder:
                recorder(cmd)
            if not dry_run:
                proc = await asyncio.create_subprocess_exec(
                    self.executable,
                    *self.args, *args,
                    stderr=asyncio.subprocess.PIPE,
                    stdout=stdout)
                out, err = await proc.communicate()

                rc = proc.returncode
                if not always_return and rc:
                    raise ProcessError(err.decode(os.device_encoding(sys.stderr.fileno()) or 'utf-8'))
                return rc, out, err
            else:
                return 0, None, None

        return await do_run()

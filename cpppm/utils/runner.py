import asyncio
import subprocess as sp
from pathlib import Path
from typing import Dict, Union

from .decorators import working_directory
from .. import _get_logger


class ProcessError(RuntimeError):
    pass


class Runner:
    def __init__(self, executable, cwd: Path = None, env=None, recorder=None, args=None):
        self._logger = _get_logger(self, executable)
        self.executable = str(executable.absolute()) if isinstance(executable, Path) else executable
        self.cwd = cwd
        self.env = env
        self.recorder = recorder
        self.args = args or {}

    async def run(self, *args, cwd: Union[str, Path] = None, env: Dict = None, dry_run=False, recorder=None):
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
                    stderr=asyncio.subprocess.PIPE)
                _, stderr = await proc.communicate()

                rc = proc.returncode
                if rc:
                    raise ProcessError(stderr.decode())
                return rc
            else:
                return 0

        return await do_run()

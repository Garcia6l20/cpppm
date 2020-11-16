import subprocess as sp
from pathlib import Path
from typing import Dict, Union

from .decorators import working_directory
from .. import _get_logger


class ProcessError(RuntimeError):
    pass


class Runner:
    def __init__(self, executable, cwd: Path = None, env=None, recorder=None):
        self._logger = _get_logger(self, executable)
        self.executable = str(executable.absolute()) if isinstance(executable, Path) else executable
        self.cwd = cwd
        self.env = env
        self.recorder = recorder

    def run(self, *args, cwd: Union[str, Path] = None, env: Dict = None):
        if not cwd:
            cwd = self.cwd or Path.cwd()
        if not env:
            env = self.env
        else:
            env.update(self.env)

        @working_directory(cwd=Path(cwd), env=env)
        def do_run():
            tmp = [self.executable, *args]
            self._logger.debug(f'cwd: {Path.cwd()}')
            self._logger.debug(f'cmd: {" ".join(tmp)}')
            if self.recorder:
                self.recorder(' '.join(tmp))
            result = sp.run(tmp, stderr=sp.PIPE)
            rc = result.returncode
            if rc:
                raise ProcessError(result.stderr.decode())
            return rc

        return do_run()

import subprocess as sp
from pathlib import Path

from .decorators import working_directory
from .. import _get_logger


class ProcessError(RuntimeError):
    pass


class Runner:
    def __init__(self, executable, cwd: Path = None, recorder=None):
        self._logger = _get_logger(self, executable)
        self.executable = str(executable.absolute()) if isinstance(executable, Path) else executable
        self.cwd = cwd
        self.recorder = recorder

    def run(self, *args, cwd=None):
        if not cwd:
            cwd = self.cwd or Path.cwd()

        @working_directory(cwd)
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

import subprocess as sp
from pathlib import Path

from .decorators import working_directory
from .. import _get_logger


class Runner:
    def __init__(self, executable, cwd: Path = None):
        self._logger = _get_logger(self, executable)
        self.executable = str(executable.absolute()) if isinstance(executable, Path) else executable
        self.cwd = cwd

    def run(self, *args):
        @working_directory(self.cwd or Path.cwd())
        def do_run():
            tmp = [self.executable, *args]
            self._logger.debug(f'Working dir: {Path.cwd()}')
            self._logger.debug(f'Command: {" ".join(tmp)}')
            return sp.run(tmp).returncode

        return do_run()

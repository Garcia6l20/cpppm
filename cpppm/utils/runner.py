import os
from pathlib import Path
import subprocess as sp

from .. import _get_logger

from .decorators import working_directory


class Runner:
    def __init__(self, executable, working_path: Path):
        self._logger = _get_logger(self, executable)
        self.executable = str(executable.absolute()) if isinstance(executable, Path) else executable
        self.working_path = working_path

    def run(self, *args, env=None):
        @working_directory(self.working_path)
        def do_run():
            tmp = [self.executable, *args]
            self._logger.debug(f'Working dir: {self.working_path}')
            self._logger.debug(f'Command: {" ".join(tmp)}')
            return sp.run(tmp).returncode

        return do_run()

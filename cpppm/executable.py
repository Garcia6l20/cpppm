import platform
from pathlib import Path

from .target import Target
from .utils import Runner


class Executable(Target):

    @property
    def type(self) -> str:
        return ''

    @property
    def command(self) -> str:
        return 'add_executable'

    @property
    def exe(self) -> str:
        return self.name if platform.system() == 'Windows' else './' + self.name

    @property
    def executable_path(self) -> Path:
        return self._bin_path / self.exe

    def run(self, *args, working_directory=None):
        if working_directory is None:
            working_directory = self._bin_path
        runner = Runner(self.executable_path, working_directory)
        return runner.run(*args)

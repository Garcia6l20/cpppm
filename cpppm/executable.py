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
    def binary(self) -> str:
        return self.name if platform.system() == 'Windows' else './' + self.name

    @property
    def executable_path(self) -> Path:
        return self._bin_path / self.binary

    def run(self, *args, working_directory=None):
        runner = Runner(self.executable_path, working_directory)
        return runner.run(*args)

    def __str__(self):
        return f'Executable[{self.name}]'

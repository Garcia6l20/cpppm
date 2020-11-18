import platform
from pathlib import Path

from .build.compiler import get_compiler
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

    def final_build_step(self, objs, library_paths, libraries):
        self.bin_path.parent.mkdir(exist_ok=True, parents=True)
        self.cc.link(objs, self.bin_path, library_paths=[self._lib_path, *library_paths], libraries=libraries)

    def run(self, *args, working_directory=None):
        self.build()
        runner = Runner(self.executable_path, working_directory, env={'LD_LIBRARY_PATH': str(self._lib_path)})
        return runner.run(*args)

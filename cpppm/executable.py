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

    def build(self):
        libraries = self.build_deps()

        objs = self.cc.compile(self.compile_sources, self.build_path,
                               include_paths=[self.source_path, *self.include_paths])
        self.cc.link(objs, self.bin_path, library_paths=[self._lib_path], libraries=libraries)

    def run(self, *args, working_directory=None):
        runner = Runner(self.executable_path, working_directory, env={'LD_LIBRARY_PATH': str(self._lib_path)})
        return runner.run(*args)

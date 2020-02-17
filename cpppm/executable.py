import platform

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

    def run(self, *args, working_directory=None):
        from .project import Project
        runner = Runner(Project.root_project.bin_path.joinpath(self.exe), working_directory)
        return runner.run(*args)

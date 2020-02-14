import platform

from .target import Target


class Executable(Target):

    @property
    def type(self) -> str:
        return ''

    @property
    def command(self) -> str:
        return 'add_executable'

    @property
    def exe(self) -> str:
        return self.name + '.exe' if platform.system() == 'Windows' else self.name

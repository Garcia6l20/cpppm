from .target import Target


class Library(Target):
    static: bool = False

    @property
    def shared(self) -> bool:
        return not self.static

    @shared.setter
    def shared(self, value: bool):
        self.static = not value

    @property
    def type(self) -> str:
        return 'STATIC' if self.static else 'SHARED'

    @property
    def command(self) -> str:
        return 'add_library'

    @property
    def exe(self) -> str:
        raise RuntimeError(f'{self.name} is not an executable')

    def __str__(self):
        return f'Library[{self.name}]'

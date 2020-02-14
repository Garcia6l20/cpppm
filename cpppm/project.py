import inspect
import os
import stat
from pathlib import Path
import platform
from typing import List, Union, final, cast
import contextlib

from .target import Target
from .executable import Executable
from .library import Library
from . import _jenv, _logger


@contextlib.contextmanager
def working_directory(path: Path, create=True, *args, **kwargs):
    """Changes working directory and returns to previous on exit."""
    prev_cwd = Path.cwd()
    if create:
        path.mkdir(exist_ok=True)
    os.chdir(str(path))
    try:
        yield
    finally:
        os.chdir(str(prev_cwd))


@final
class Project:
    root_project: 'Project' = None
    projects: List['Project'] = []
    dependencies: List[str] = []
    build_path: Path = None
    main_target: Target = None

    def __init__(self, name):
        stack_trace = inspect.stack()
        module_frame = None
        for frame in stack_trace:
            if frame.function == '<module>':
                module_frame = frame
                break
        self.build_script = Path(module_frame[1])
        self.root_path = self.build_script.parent
        self.build_path = self.root_path.joinpath('build-cpppm')
        self.bin_path = self.build_path.joinpath('bin')
        self.lib_path = self.build_path.joinpath('lib')

        self.name = name
        self.libraries: List[Library] = []
        self.executables: List[Executable] = []
        if Project.root_project is None:
            Project.root_project = self
        Project.projects.append(self)

    def main_executable(self) -> Executable:
        """Add the default project executable (same name as project)
        """
        if self.main_target is not None:
            raise RuntimeError("You cannot use both Project.main_library and Project.main_executable")
        self.main_target = self.executable(self.name)
        return cast(Executable, self.main_target)

    def executable(self, name) -> Executable:
        """Add an executable to the project"""
        executable = Executable(name, self.root_path)
        self.executables.append(executable)
        return executable

    def main_library(self) -> Library:
        """Add the default project library (same name as project)"""
        if self.main_target is not None:
            raise RuntimeError("You cannot use both Project.main_library and Project.main_executable")
        self.main_target = self.library(self.name)
        return cast(Library, self.main_target)

    def library(self, name) -> Library:
        """Add a library to the project"""
        library = Library(name, self.root_path)
        self.libraries.append(library)
        return library

    @property
    def targets(self) -> List[Target]:
        targets: List[Target] = self.libraries.copy()
        targets.extend(self.executables)
        return targets

    def generate(self):
        """Generates CMake stuff"""

        def to_source_dir(path: Union[Path, str]):
            return path.relative_to(self.root_path).as_posix() if isinstance(path, Path) else path

        def to_library(lib: Union[Library, str]):
            return lib.name if type(lib) is Library else lib

        _jenv.filters.update({
            "to_source_dir": to_source_dir,
            "to_library": to_library,
        })
        jlists = _jenv.get_template('CMakeLists.txt.j2')
        lists_file = open(self.root_path / 'CMakeLists.txt', 'w')
        lists = jlists.render({'project': self})
        _logger.debug(lists)
        lists_file.write(lists)

    def build(self, target: str = 'all'):

        @working_directory(self.build_path)
        def do_build():
            os.system('pwd')
            print(f'cmake {str(self.root_path.absolute())}')
            os.system(f'cmake {str(self.root_path.absolute())}')
            os.system(f'cmake --build . --target {target}')
        do_build()

    def run(self, target: str, *args):

        if target is None:
            if self.main_target is None:
                raise RuntimeError(r'No main target defined')
            target = self.main_target.name

        target = self.target(target)

        @working_directory(self.bin_path)
        def do_run():
            os.system(f'./{target.exe} {" ".join(*args)}')
        do_run()

    def target(self, name: str) -> Target:
        return next(filter(lambda t: t.name == name, self.targets))

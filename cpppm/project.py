import inspect
import os
from pathlib import Path
from typing import List, Union, final, cast

from cpppm.utils import Runner

from . import _jenv, _get_logger
from .executable import Executable
from .library import Library
from .target import Target


@final
class Project:
    root_project: 'Project' = None
    projects: List['Project'] = []
    dependencies: List[str] = []
    main_target: Target = None
    build_path: Path = None

    @staticmethod
    def set_build_path(path: Path):
        for proj in Project.projects:
            proj.build_path = path.absolute()
        Project.build_path = path.absolute()

    def __init__(self, name):
        self._logger = _get_logger(self, name)
        stack_trace = inspect.stack()
        module_frame = None
        for frame in stack_trace:
            if frame.function == '<module>':
                module_frame = frame
                break
        self.build_script = Path(module_frame[1])
        self._root_path = self.build_script.parent.absolute()
        self.build_path = Project.build_path or self._root_path.joinpath('build-cpppm')

        self._logger.debug(f'Build dir: {self.build_path.absolute()}')
        self._logger.debug(f'Source dir: {self.source_path.absolute()}')

        self.name = name
        self.libraries: List[Library] = []
        self.executables: List[Executable] = []

        self.default_executable = None

        if Project.root_project is None:
            Project.root_project = self
        Project.projects.append(self)

    @property
    def source_path(self):
        return self._root_path

    @property
    def bin_path(self):
        return self.build_path.joinpath('bin')

    @property
    def lib_path(self):
        return self.build_path.joinpath('lib')

    def main_executable(self) -> Executable:
        """Add the default project executable (same name as project)
        """
        if self.main_target is not None:
            raise RuntimeError("You cannot use both Project.main_library and Project.main_executable")
        self.main_target = self.executable(self.name)
        return cast(Executable, self.main_target)

    def executable(self, name) -> Executable:
        """Add an executable to the project"""
        executable = Executable(name, self.source_path)
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
        library = Library(name, self.source_path)
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
            return path.relative_to(self.source_path).as_posix() if isinstance(path, Path) else path

        def to_library(lib: Union[Library, str]):
            return lib.name if type(lib) is Library else lib

        _jenv.filters.update({
            "to_source_dir": to_source_dir,
            "to_library": to_library,
        })
        jlists = _jenv.get_template('CMakeLists.txt.j2')
        lists_file = open(self.source_path / 'CMakeLists.txt', 'w')
        lists = jlists.render({'project': self})
        # self._logger.debug(lists)
        lists_file.write(lists)

    def build(self, target: str = None):
        runner = Runner("cmake", self.build_path)
        runner.run(str(self.source_path.absolute()))
        args = ['--build', '.']
        if target:
            args.extend(('--target', {target}))
        runner.run(*args)

    def run(self, target: str, *args):
        target = target or self.default_executable or self.main_target
        if target is None:
            raise RuntimeError(r'No default executable defined')

        if not isinstance(target, Target):
            target = self.target(target)

        self._logger.debug(f'Build path: {self.build_path}')
        self._logger.debug(f'Bin path: {self.bin_path}')

        runner = Runner(target.exe, self.bin_path)
        runner.run(*args)

    def target(self, name: str) -> Target:
        return next(filter(lambda t: t.name == name, self.targets))

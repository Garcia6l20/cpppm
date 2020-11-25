import asyncio
import importlib.util
import inspect
import re
import shutil
import sys

from pathlib import Path
from typing import Union, cast, Any, Dict, Set

from conans.model.requires import ConanFileReference

from . import _jenv, _get_logger, get_conan
from .config import config
from .executable import Executable
from .library import Library
from .target import Target
from .utils.decorators import classproperty, collectable


def load_project(path=Path.cwd(), name=None):
    assert path.is_dir()
    if not name:
        name = path.name
    sys.path.append(path)  # add project's path to PYTHONPATH to allow easy extending
    spec = importlib.util.spec_from_file_location(name, path.joinpath('project.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.project


class Installation:
    libraries = 'lib'
    archives = 'lib'
    binaries = 'bin'
    headers = 'include'


class Project:
    installation = Installation()

    _root_project: 'Project' = None
    current_project: 'Project' = None
    projects: Set['Project'] = set()
    main_target: Target = None
    build_path: Path = None
    __all_targets: Set[Target] = set()
    _pkg_libraries: Dict[str, 'cpppm.conans.PackageLibrary'] = dict()

    # export commands from CMake (can be used by clangd)
    export_compile_commands = False
    verbose_makefile = False
    settings = None

    def __init__(self, name, version: str = None, package_name=None, build_path=None):
        self.name = name
        if not package_name:
            package_name = name
        self.package_name = package_name
        self.version = version
        self.license = None
        self._logger = _get_logger(self, name)
        stack_trace = inspect.stack()
        module_frame = None
        for frame in stack_trace:
            if frame.function == '<module>':
                module_frame = frame
                break
        self.script_path = Path(module_frame[1]).resolve()
        self._root_path = self.script_path.parent.absolute()

        # adjust output dir
        if not Project.root_project:
            self.build_relative = '.'
            config.init(self.source_path)
            Project.settings = config._settings
            self.build_path = build_path or config._build_path
            Project._root_project = self
        else:
            self._root_project = Project._root_project
            self.build_relative = self.source_path.relative_to(Project.root_project.source_path)
            self.build_path = (Project.root_project.build_path / self.build_relative).absolute()
        self.build_path.mkdir(exist_ok=True, parents=True)

        self._logger.debug(f'Build dir: {self.build_path.absolute()}')
        self._logger.debug(f'Source dir: {self.source_path.absolute()}')

        self._libraries: Set[Library] = set()
        self._executables: Set[Executable] = set()
        self._requires: Set[str] = set()
        self._build_requires: Set[str] = set()
        self._options: Dict[str, Any] = {"fPIC": [True, False], "shared": [True, False]}
        self._default_options: Dict[str, Any] = {"fPIC": True, "shared": False}
        self._build_modules: Set[str] = set()
        self._requires_options: Dict[str, Any] = dict()

        self._default_executable = None
        self._conan_infos = None
        self._conan_refs = None

        self.test_folder = None

        self.generators = []
        self._subprojects: Set[Project] = set()

        Project.projects.add(self)
        Project.current_project = self

    @classproperty
    def all(cls):
        return cls.__all_targets

    @classproperty
    def root_project(cls) -> 'Project':
        return cls._root_project

    @staticmethod
    def get_project(name) -> 'Project':
        for project in Project.projects:
            if project.name == name:
                return project  # already included

    @property
    def default_executable(self) -> Executable:
        return self._default_executable or self.main_target

    @default_executable.setter
    def default_executable(self, exe: Executable):
        self._default_executable = exe

    @property
    def source_path(self) -> Path:
        return self._root_path

    @property
    def bin_path(self) -> Path:
        return Project._root_project.build_path / 'bin'

    @property
    def lib_path(self) -> Path:
        return Project._root_project.build_path / 'lib'

    @property
    def subprojects(self) -> Set['Project']:
        return self._subprojects

    def _target_paths(self, root: str) -> [Path, Path]:
        root = Path(root) if root is not None else self.source_path
        if not root.is_absolute():
            build_root = self.build_path / root
        else:
            build_root = self.build_path / root.relative_to(self.source_path)
        return root.absolute(), build_root.absolute()

    def main_executable(self, root: str = None, **kwargs) -> Executable:
        """Add the default project executable (same name as project)
        """
        if self.main_target is not None:
            raise RuntimeError("You cannot use both Project.main_library and Project.main_executable")
        self.main_target = self.executable(self.name, root, **kwargs)
        return cast(Executable, self.main_target)

    def executable(self, name, root: str = None, **kwargs) -> Executable:
        """Add an executable to the project"""
        executable = Executable(name, *self._target_paths(root), **kwargs)
        self._executables.add(executable)
        Project.__all_targets.add(executable)
        return executable

    def main_library(self, root: str = None, **kwargs) -> Library:
        """Add the default project library (same name as project)"""
        if self.main_target is not None:
            raise RuntimeError("You cannot use both Project.main_library and Project.main_executable")
        self.main_target = self.library(self.name, root, **kwargs)
        return cast(Library, self.main_target)

    def library(self, name, root: str = None, **kwargs) -> Library:
        """Add a library to the project"""
        library = Library(name, *self._target_paths(root), **kwargs)
        self._libraries.add(library)
        Project.__all_targets.add(library)
        return library

    @property
    def targets(self) -> Set[Target]:
        targets: Set[Target] = self._libraries.copy()
        targets.update(self._executables)
        return targets

    @staticmethod
    def get_target(name):
        for target in Project.__all_targets:
            if target.name == name:
                return target

    @collectable(subprojects)
    def requires(self):
        return self._requires

    @collectable(subprojects)
    def build_requires(self):
        return self._build_requires

    @collectable(subprojects)
    def requires_options(self):
        return self._requires_options

    @collectable(subprojects)
    def options(self):
        return self._options

    @collectable(subprojects)
    def default_options(self):
        return self._default_options

    @property
    def dependencies_options(self):
        return dict(filter(lambda it: re.compile(r'.+:.+').match(it[0]), self.default_options.items()))

    @collectable(subprojects)
    def build_modules(self):
        return self._build_modules

    @property
    def conan_refs(self):
        return [ConanFileReference.loads(req) for req in self.requires] + [ConanFileReference.loads(req) for req in
                                                                           self.build_requires]

    @property
    def conan_packages(self):
        return [ref.name for ref in self.conan_refs]

    @property
    def uses_conan(self):
        return bool(len(self.conan_packages))

    def install_requirements(self):
        if not self.uses_conan:
            self._logger.info('project has no requirements')
            return
        conan = get_conan()

        open(str(self.build_path / 'conanfile.txt'), 'w').write(
            _jenv.get_template('conanfile.txt.j2').render({
                'requires': self.requires,
                'build_requires': self.build_requires,
                'options': self.requires_options,
            }))

        settings = [f'{k}={v}' for k, v in Project.settings.items()]

        conan_file = str(self.build_path / 'conanfile.txt')

        # infos, conan_file_data = conan.info(conan_file,
        #                                settings=settings, build=["outdated"], update=True)
        install_infos = conan.install(conan_file, cwd=self.build_path,
                                      settings=settings, build=["outdated"], update=True, env={
                                          f'CC={config.cc}',
                                          f'CXX={config.cxx}',
                                      })

        from cpppm.conans import PackageLibrary

        for info in install_infos['installed']:
            if info['recipe']['name'] not in Project._pkg_libraries:
                pkg_lib = PackageLibrary(info)
                Project._pkg_libraries[pkg_lib.name] = pkg_lib
        for pkg_lib in Project._pkg_libraries.values():
            pkg_lib.resolve_deps()

        for target in Project.__all_targets:
            for lib in target.link_libraries:
                if isinstance(lib, str):
                    target._link_libraries.remove(lib)
                    target._link_libraries.add(Project._pkg_libraries[lib])

    def conan_infos(self, pkg_name):
        for installed in self._conan_infos['installed']:
            if installed['recipe']['name'] == pkg_name:
                for pkg in installed['packages']:
                    return pkg['cpp_info']

    @property
    def is_root(self):
        return self.build_path == config._build_path

    async def build(self, target: Union[str, Target] = None, jobs: int = None) -> int:
        if target:
            target = target if isinstance(target, Target) else self.target(target)

        if not target:
            builds = set()
            for target in self.all:
                builds.add(target.build())
            await asyncio.gather(*builds)
        else:
            await target.build()
        return 0

    async def run(self, target_name: str, *args):
        target = target_name or self.default_executable or self.main_target
        if target is None:
            self._logger.warning(f'No default target defined')
            return -1

        if not isinstance(target, Target):
            target = self.target(target)
        if not target:
            raise RuntimeError(f'Target not found: {target_name}')

        if not isinstance(target, Executable):
            self._logger.warning(f'Cannot execute target: {target.name} (not an executable)')
        else:
            return await target.run(*args)

    def target(self, name: str) -> Target:
        for t in self.targets:
            if t.name == name:
                return t
        for project in self.subprojects:
            t = project.target(name)
            if t:
                return t

    def subproject(self, name: str, path: Union[str, Path] = None) -> 'Project':
        if path is None:
            path = self.source_path.joinpath(name)
        if isinstance(path, str):
            path = Path(path)

        if not path.is_absolute():
            path = (self.source_path / path).resolve().absolute()

        project = Project.get_project(name)
        if project is not None:
            if project == self:
                raise RuntimeError('Recursive project inclusion is not allowed')
            return project  # already included

        subproject = load_project(path, name)
        Project.current_project = self
        self._subprojects.add(subproject)
        return subproject

    def set_event(self, func):
        setattr(self, func.__name__, func)

    async def install(self, destination: Union[str, Path]):
        destination = Path(destination)

        logger = self._logger

        def _copy(self: Path, target: Path):
            logger.info(f'Copying {self} -> {target}')

            target.mkdir(parents=True, exist_ok=True)
            shutil.copy(str(self.absolute().as_posix()), str(target.absolute().as_posix()))

        Path.copy = _copy

        # copy executables
        for exe in self._executables:
            if exe.install:
                exe.bin_path.copy(destination / self.installation.binaries)

        # copy libraries/headers
        for lib in self._libraries:
            if lib.install:
                if lib.binary:
                    lib.bin_path.copy(destination / self.installation.binaries)
                if lib.library:
                    lib.lib_path.copy(destination / self.installation.libraries)
                for header in lib.public_headers.absolute():
                    header.copy(destination / self.installation.headers)

        # subprojects
        installs = set()
        for project in self.subprojects:
            installs.add(project.install(destination))
        await asyncio.gather(*installs)

    def package(self):
        conanfile_path = self.source_path / 'conanfile.py'
        self._logger.info("You have no conan file... I'm creating it for you !")
        open(conanfile_path, 'w').write(_jenv.get_template('conanfile.py.j2').render({'project': self}))

        conan = get_conan()
        conan.create(str(conanfile_path.absolute()), test_folder=self.test_folder,
                     options=[f'{k}={v}' for k, v in self.requires_options.items()])


def current_project() -> Project:
    return Project.current_project


def root_project() -> Project:
    if not Project.root_project:
        # project is not set means we are being called from conan
        # just try to load project.py from cwd
        Project.root_project = load_project()
    return Project.root_project

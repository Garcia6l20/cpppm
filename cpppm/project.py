import importlib.util
import inspect
import re
import shutil

from pathlib import Path
from typing import List, Union, cast, Any, Dict, Set

from conans.model.requires import ConanFileReference

from . import _jenv, _get_logger, _get_build_path, get_conan, get_settings
from .build.compiler import get_compiler
from .executable import Executable
from .library import Library
from .target import Target
from .utils import Runner
from .utils.decorators import classproperty, collectable


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
    _profile = 'default'

    # export commands from CMake (can be used by clangd)
    export_compile_commands = False
    verbose_makefile = False

    cc = get_compiler('c++')

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
            self.build_path = build_path or _get_build_path(self.source_path)
            Project._root_project = self
            Project.project_settings = get_settings()
            self.build_relative = '.'

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
        self._settings: Set[str, Any] = {"os", "compiler", "build_type", "arch"}
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
    def profile(cls):
        return cls._profile

    @classmethod
    def set_profile(cls, profile):
        cls._profile = profile or 'default'
        conan = get_conan()
        pr = conan.read_profile(cls._profile)
        cls.project_settings = dict(pr.settings)

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
    def subprojects(self) -> List['Project']:
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
    def settings(self):
        return self._settings

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

        settings = [f'{k}={v}' for k, v in Project.project_settings.items()]

        conan_file = str(self.build_path / 'conanfile.txt')

        # infos, conan_file_data = conan.info(conan_file,
        #                                settings=settings, build=["outdated"], update=True)
        install_infos = conan.install(conan_file, cwd=self.build_path,
                                      settings=settings, build=["outdated"], update=True)

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

    def _conan_paths(self, pkg_name, path_name):
        infos = self.conan_infos(pkg_name)
        if infos:
            return [Path(infos['rootpath']) / path for path in infos[path_name]]

    def conan_library_paths(self, pkg_name):
        return self._conan_paths(pkg_name, 'libdirs')

    def conan_link_libraries(self, pkg_name, infos=None):
        infos = infos or self.conan_infos(pkg_name)
        system_libs = []
        libs = []
        if infos:
            if 'libs' in infos:
                libs.extend(infos['libs'])
            if 'system_libs' in infos:
                system_libs.extend(infos['system_libs'])
            if 'components' in infos:
                for infos in infos['components'].values():
                    comp_sys_libs, comp_libs = self.conan_link_libraries(pkg_name, infos)
                    system_libs.extend(comp_sys_libs)
                    libs.extend(comp_libs)
        return system_libs, libs

    def conan_include_paths(self, pkg_name):
        return self._conan_paths(pkg_name, 'includedirs')

    def conan_defines(self, pkg_name):
        infos = self.conan_infos(pkg_name)
        if 'defines' in infos:
            return infos['defines']
        elif 'components' in infos:
            for infos in infos['components'].values():
                if 'defines' in infos:
                    return infos['defines']
        return []

    def conan_build_paths(self, pkg_name):
        return self._conan_paths(pkg_name, 'builddirs')

    def conan_res_paths(self, pkg_name):
        return self._conan_paths(pkg_name, 'resdirs')

    @property
    def is_root(self):
        return self.build_path == _get_build_path(self.source_path)

    def generate(self):
        """Generates CMake stuff"""
        self._logger.debug('TODO remove Project.generate method')

    def configure(self, *args) -> int:
        self._logger.debug('TODO remove Project.configure method')

    def _cmake_runner(self):
        return Runner("cmake", self.build_path)

    def build(self, target: Union[str, Target] = None, jobs: int = None) -> int:
        if not target:
            t = self.main_target
        else:
            t = target if isinstance(target, Target) else self.target(target)

        if not t:
            for subproj in self.subprojects:
                subproj.build(jobs=jobs)
        else:
            t.build()
        return 0

    def run(self, target_name: str, *args):
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
            return target.run(*args)

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

        spec = importlib.util.spec_from_file_location(name, path.joinpath('project.py'))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        subproject = module.project
        Project.current_project = self
        self._subprojects.add(subproject)
        return subproject

    def set_event(self, func):
        setattr(self, func.__name__, func)

    def install(self, destination: Union[str, Path]):
        destination = Path(destination)

        logger = self._logger

        def _copy(self: Path, target: Path):
            logger.info(f'Copying {self} -> {target}')

            target.mkdir(parents=True, exist_ok=True)
            shutil.copy(str(self.absolute().as_posix()), str(target.absolute().as_posix()))

        Path.copy = _copy

        # copy executables
        for exe in self._executables:
            exe.build()
            exe.bin_path.copy(destination / self.installation.binaries)

        # copy libraries/headers
        for lib in self._libraries:
            lib.build()
            if lib.binary:
                lib.bin_path.copy(destination / self.installation.binaries)
            if lib.library:
                lib.lib_path.copy(destination / self.installation.libraries)
            for header in lib.public_headers.absolute():
                header.copy(destination / self.installation.headers)

        # subprojects
        for project in self.subprojects:
            project.install(destination)

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
    return Project.root_project

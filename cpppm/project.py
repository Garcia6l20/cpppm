import hashlib
import importlib.util
import inspect
import os
import re
import sys
from pathlib import Path
from typing import List, Union, cast, Any, Dict, Optional, Type

from conans.client.recorder.action_recorder import ActionRecorder
from conans.model.requires import ConanFileReference
from cpppm.layout import Layout, DefaultProjectLayout, DefaultDistLayout, LayoutConverter

from . import _jenv, _get_logger, _get_build_path, get_conan, get_settings
from .executable import Executable
from .library import Library
from .target import Target
from .utils import Runner
from .utils.decorators import classproperty, collectable


class Project:
    _root_project: 'Project' = None
    current_project: 'Project' = None
    projects: List['Project'] = []
    main_target: Target = None
    build_path: Path = None
    __all_targets: List[Target] = []
    _profile = 'default'

    layout: Type[Layout] = DefaultProjectLayout
    dist_layout: Type[Layout] = DefaultDistLayout

    # export commands from CMake (can be used by clangd)
    export_compile_commands = False
    verbose_makefile = False

    def __init__(self, name, version: str = None, package_name=None, project_layout: Optional[Type[Layout]] = None):
        self.name = name
        if not package_name:
            package_name = name
        self.package_name = package_name
        self.version = version
        self.layout = project_layout or Project.layout
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
            self.build_path = _get_build_path(self.source_path)
            Project._root_project = self
            Project.project_settings = get_settings()
            self.build_relative = '.'
        else:
            self._root_project = Project._root_project
            self.build_relative = self.source_path.relative_to(Project.root_project.source_path)
            self.build_path = (Project.root_project.build_path / self.build_relative).absolute()
        self.build_path.mkdir(exist_ok=True, parents=True)
        self.layout.public_includes += [str(self.build_path.as_posix())]

        self._logger.debug(f'Build dir: {self.build_path.absolute()}')
        self._logger.debug(f'Source dir: {self.source_path.absolute()}')

        self._libraries: List[Library] = []
        self._executables: List[Executable] = []
        self._requires: List[str] = list()
        self._build_requires: List[str] = list()
        self._settings: List[str, Any] = {"os", "compiler", "build_type", "arch"}
        self._options: Dict[str, Any] = {"fPIC": [True, False], "shared": [True, False]}
        self._default_options: Dict[str, Any] = {"fPIC": True, "shared": False}
        self._build_modules: List[str] = []
        self._requires_options: Dict[str, Any] = dict()

        self._default_executable = None
        self._conan_infos = None
        self._conan_refs = None

        self.test_folder = None

        self.generators = []
        self._subprojects: List[Project] = list()

        Project.projects.append(self)
        Project.current_project = self

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
    def get_project(name):
        for project in Project.projects:
            if project.name == name:
                return project  # already included

    @property
    def default_executable(self):
        return self._default_executable or self.main_target

    @default_executable.setter
    def default_executable(self, exe: Executable):
        self._default_executable = exe

    @property
    def source_path(self):
        return self._root_path

    @property
    def bin_path(self):
        return Project._root_project.build_path.joinpath('bin')

    @property
    def lib_path(self):
        return Project._root_project.build_path.joinpath('lib')

    @property
    def subprojects(self):
        return self._subprojects

    @property
    def dist_converter(self):
        return LayoutConverter(self.layout, self.dist_layout)

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
        self._executables.append(executable)
        Project.__all_targets.append(executable)
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
        self._libraries.append(library)
        Project.__all_targets.append(library)
        return library

    @property
    def targets(self) -> List[Target]:
        targets: List[Target] = self._libraries.copy()
        targets.extend(self._executables)
        # for _, project in self.subprojects.items():
        #     targets.extend(project.targets)
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
            self._logger.debug('project has no requirements')
            return
        conan = get_conan()
        recorder = ActionRecorder()

        open(str(self.build_path / 'conanfile.txt'), 'w').write(
            _jenv.get_template('conanfile.txt.j2').render({
                'requires': self.requires,
                'build_requires': self.build_requires,
                'options': self.requires_options,
            }))

        settings = [f'{k}={v}' for k, v in Project.project_settings.items()]

        # profile_host = ProfileData(profiles=profile_names, settings=settings, options=self.options,
        #                            env=None)

        conan.install(str(self.build_path / 'conanfile.txt'), cwd=self.build_path,
                      settings=settings, build=["outdated"], update=True)
        # conan.out.flush()

        self._conan_infos = recorder.get_info(conan.app.config.revisions_enabled)

    @property
    def is_root(self):
        return self.build_path == _get_build_path(self.source_path)

    def generate(self):
        """Generates CMake stuff"""

        # generate subprojects
        for project in self.subprojects:
            self._logger.debug(f'Generating {project.name} ({project.source_path})')
            project.generate()

        def relative_source_path(path: Union[Path, str]):
            return path.absolute().relative_to(self.source_path).as_posix() if isinstance(path, Path) else path

        def absolute_path(path: Path):
            return path.absolute().as_posix()

        def relative_build_path(path: Union[Path, str]):
            if not isinstance(path, Path):
                return (self.build_path / Path(path)).as_posix()
            elif path.is_absolute():
                return path.absolute().relative_to(self.build_path).as_posix()
            else:
                return (self.build_path / Path(path)).as_posix()

        def to_library(lib: Union[Library, str]):
            if type(lib) is Library:
                return lib.name
            elif lib in Project.root_project.conan_packages:
                return f'CONAN_PKG::{lib}'
            else:
                return lib

        def to_dependencies(deps: List[Union[Path, Target]], project: Optional[Project]):
            str_deps = []
            for dep in deps:
                if isinstance(dep, Target):
                    str_deps.append(dep.name)
                elif isinstance(dep, Path):
                    path = os.path.relpath(dep, project.build_path)
                    str_deps.append(path)
                else:
                    str_deps.append(dep)
            return ' '.join(str_deps)

        self.build_path.mkdir(exist_ok=True)
        _jenv.filters.update({
            'absolute_path': absolute_path,
            "relative_source_path": relative_source_path,
            "relative_build_path": relative_build_path,
            "to_library": to_library,
            "to_dependencies": to_dependencies,
        })
        jlists = _jenv.get_template('CMakeLists.txt.j2')
        lists = jlists.render({
            'project': self,
            'cache': {
                'subdirs': []
            },
            'root_project': Project.root_project,
            'python': Path(sys.executable).as_posix(),
            'pythonpath': self.script_path.parent.parent.absolute().as_posix(),
        })
        if Path.exists(self.build_path / 'CMakeLists.txt'):
            old_sha1 = hashlib.sha1(open(str(self.build_path / 'CMakeLists.txt'), 'r').read().encode()).hexdigest()
            sha1 = hashlib.sha1(lists.encode()).hexdigest()
            if sha1 != old_sha1:
                open(str(self.build_path / 'CMakeLists.txt'), 'w').write(lists)
            else:
                self._logger.debug(f'{self.name} CMakeLists.txt is up-to-date')
        else:
            open(str(self.build_path / 'CMakeLists.txt'), 'w').write(lists)

        if Project.root_project == self:
            # when called from conan, _export_compile_commands attribute does not exist !?!
            if self.export_compile_commands:
                self._logger.info('Exporting compilitation commands')
                source_compile_commands = self.source_path / 'compile_commands.json'
                build_compile_commands = self.build_path / 'compile_commands.json'
                if source_compile_commands.exists():
                    source_compile_commands.unlink()
                source_compile_commands.symlink_to(build_compile_commands)

    def configure(self, *args) -> int:
        runner = Runner("cmake", self.build_path)
        return runner.run(
            f'-DCMAKE_BUILD_TYPE={Project.project_settings["build_type"]}',
            f'-DCMAKE_EXPORT_COMPILE_COMMANDS={"ON" if Project.export_compile_commands else "OFF"}',
            f'-DCMAKE_VERBOSE_MAKEFILE={"ON" if Project.verbose_makefile else "OFF"}',
            *args, '.')

    def _cmake_runner(self):
        return Runner("cmake", self.build_path)

    def build(self, target: str = None, jobs: int = None) -> int:
        t = self.target(target)
        if isinstance(t, Library) and t.is_header_only:
            return 0  # skip header-only build requests
        runner = self._cmake_runner()
        args = ['--build', '.']
        if target:
            args.extend(('--target', target))
        args.extend(('--config', Project.build_type))
        if not jobs:
            args.append('-j')
        else:
            args.extend(('-j', jobs))
        return runner.run(*args)

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
        self._subprojects.append(subproject)
        return subproject

    def set_event(self, func):
        setattr(self, func.__name__, func)

    def install(self, destination: Union[str, Path]):
        # if isinstance(destination, Path):
        #     destination = str(destination)
        runner = Runner("cmake")
        return runner.run('--install', str(self.build_path), '--prefix', str(destination))
        #
        # logger = self._logger
        #
        # def _copy(self: Path, target: Path):
        #     logger.info(f'Copying {self} -> {target}')
        #
        #     target.mkdir(parents=True, exist_ok=True)
        #     shutil.copy(str(self.absolute().as_posix()), str(target.absolute().as_posix()))
        #
        # Path.copy = _copy
        #
        # conv = self.dist_converter
        # conv.anchor = destination
        # conv.root = Path(os.path.commonpath([self.build_path, self.source_path]))
        #
        # def do_install(item):
        #     if isinstance(item, tuple):
        #         item[0].copy(item[1])
        #     else:
        #         for src, dst in item:
        #             src.copy(dst)
        #
        # # copy executables
        # for exe in self._executables:
        #     do_install(conv(exe.bin_path))
        #
        # # copy libraries/headers
        # for lib in self._libraries:
        #     if lib.binary:
        #         do_install(conv(lib.bin_path))
        #     if lib.library:
        #         do_install(conv(lib.lib_path))
        #
        # try:
        #     for lib in self._libraries:
        #         do_install(conv(lib.public_headers))
        #     do_install(conv(self.build_modules))
        # except UnmappedToLayoutError as err:
        #     raise UnmappedToLayoutError(err.item,
        #                                 f'You are trying to install {err.item} '
        #                                 'but is not defined in the project layout, '
        #                                 'you have to extend the default layout with your own paths '
        #                                 f'(during installation of {self.name})')
        #
        # # subprojects
        # for project in self.subprojects:
        #     project.install(destination)

    def package(self):
        conanfile_path = self.source_path / 'conanfile.py'
        self._logger.info("You have no conan file... I'm creating it for you !")
        open(conanfile_path, 'w').write(_jenv.get_template('conanfile.py.j2').render({'project': self}))

        conan = get_conan()
        conan.create(str(conanfile_path.absolute()), test_folder=self.test_folder,
                     options=[f'{k}={v}' for k, v in self.requires_options.items()])

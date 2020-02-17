import inspect
import sys
from pathlib import Path
from typing import List, Union, final, cast, Any, Dict

from cpppm.utils.pathlist import PathList

from conans.client.conan_api import Conan, get_graph_info
from conans.client.manager import deps_install
from conans.client.recorder.action_recorder import ActionRecorder
from conans.model.requires import ConanFileReference
from . import _jenv, _get_logger
from .executable import Executable
from .library import Library
from .target import Target
from .utils import Runner
from .utils.decorators import list_property


@final
class Project:
    root_project: 'Project' = None
    projects: List['Project'] = []
    main_target: Target = None
    build_path: Path = None
    build_type = 'Debug'
    settings = []

    @staticmethod
    def set_build_path(path: Path):
        for proj in Project.projects:
            proj.build_path = path.absolute()
        Project.build_path = path.absolute()

    def __init__(self, name, version: str = None):
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
        self.build_path = Project.build_path or self._root_path.joinpath('build-cpppm')

        self._logger.debug(f'Build dir: {self.build_path.absolute()}')
        self._logger.debug(f'Source dir: {self.source_path.absolute()}')

        self.name = name
        self.version = version
        self._libraries: List[Library] = []
        self._executables: List[Executable] = []
        self._requires: List[str] = []
        self._build_requires: List[str] = []
        self.requires_options: Dict[str, Any] = {}

        self.default_executable = None

        self._uses_conan = False
        self._conan_infos = None
        self._conan_refs = None
        self.conan_packages = []

        self.generators = []

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
    def uses_conan(self):
        return self._uses_conan

    @property
    def lib_path(self):
        return self.build_path.joinpath('lib')

    @list_property
    def requires(self):
        return self._requires

    @list_property
    def build_requires(self):
        return self._build_requires

    def _target_paths(self, root: str) -> [Path, Path]:
        root = Path(root) if root is not None else self.source_path
        if not root.is_absolute():
            build_root = self.build_path / root
        else:
            build_root = self.build_path / root.relative_to(self.source_path)
        return root.absolute(), build_root.absolute()

    def main_executable(self, root: str = None) -> Executable:
        """Add the default project executable (same name as project)
        """
        if self.main_target is not None:
            raise RuntimeError("You cannot use both Project.main_library and Project.main_executable")
        self.main_target = self.executable(self.name, root)
        return cast(Executable, self.main_target)

    def executable(self, name, root: str = None) -> Executable:
        """Add an executable to the project"""
        executable = Executable(name, *self._target_paths(root))
        self._executables.append(executable)
        return executable

    def main_library(self, root: str = None) -> Library:
        """Add the default project library (same name as project)"""
        if self.main_target is not None:
            raise RuntimeError("You cannot use both Project.main_library and Project.main_executable")
        self.main_target = self.library(self.name, root)
        return cast(Library, self.main_target)

    def library(self, name, root: str = None) -> Library:
        """Add a library to the project"""
        library = Library(name,  *self._target_paths(root))
        self._libraries.append(library)
        return library

    @property
    def targets(self) -> List[Target]:
        targets: List[Target] = self._libraries.copy()
        targets.extend(self._executables)
        return targets

    def install_requirements(self):
        if len(self._requires) == 0 and len(self._build_requires) == 0:
            self._logger.debug('project has no requirements')
            return
        conan = Conan()
        conan.create_app()
        self._conan_refs = [ConanFileReference.loads(req) for req in self.requires]
        self._conan_refs.extend([ConanFileReference.loads(req) for req in self.build_requires])
        self.conan_packages = [ref.name for ref in self._conan_refs]
        recorder = ActionRecorder()
        manifest_folder = None
        manifest_verify = False
        manifest_interactive = False
        lockfile = None
        profile_names = None
        Project.settings.append(f'build_type={Project.build_type}')
        options = [f'{key}={value}' for key, value in self.requires_options.items()]
        env = None
        graph_info = get_graph_info(profile_names, Project.settings, options, env, self.build_path, None,
                                    conan.app.cache, conan.app.out,
                                    name=None, version=None, user=None, channel=None,
                                    lockfile=lockfile)
        remotes = conan.app.load_remotes(remote_name=None, update=True)
        deps_install(app=conan.app,
                     ref_or_path=self._conan_refs,
                     install_folder=self.build_path,
                     remotes=remotes,
                     graph_info=graph_info,
                     build_modes=None,
                     update=True,
                     manifest_folder=manifest_folder,
                     manifest_verify=manifest_verify,
                     manifest_interactive=manifest_interactive,
                     generators=['cmake'],
                     no_imports=False,
                     recorder=recorder)
        self._conan_infos = recorder.get_info(conan.app.config.revisions_enabled)
        self._uses_conan = True

    def generate(self):
        """Generates CMake stuff"""

        def relative_source_path(path: Union[Path, str]):
            return path.absolute().relative_to(self.source_path).as_posix() if isinstance(path, Path) else path

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
            elif lib in self.conan_packages:
                return f'CONAN_PKG::{lib}'
            else:
                return lib

        def to_dependencies(deps: PathList):
            out = ' '.join([str(relative_build_path(dep)) for dep in deps])
            return out

        _jenv.filters.update({
            "relative_source_path": relative_source_path,
            "relative_build_path": relative_build_path,
            "to_library": to_library,
            "to_dependencies": to_dependencies,
        })
        jlists = _jenv.get_template('CMakeLists.txt.j2')
        lists_file = open(self.source_path / 'CMakeLists.txt', 'w')
        lists = jlists.render({
            'project': self,
            'cache': {
                'subdirs': []
            },
            'python': Path(sys.executable).as_posix(),
            'pythonpath': self.script_path.parent.parent.absolute().as_posix(),
        })
        # self._logger.debug(lists)
        lists_file.write(lists)

    def build(self, target: str = None) -> int:
        runner = Runner("cmake", self.build_path)
        res = runner.run(f'-DCMAKE_BUILD_TYPE={Project.build_type}', str(self.source_path.absolute()))
        if res != 0:
            return res
        args = ['--build', '.']
        if target:
            args.extend(('--target', {target}))
        args.extend(('--config', Project.build_type))
        return runner.run(*args)

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

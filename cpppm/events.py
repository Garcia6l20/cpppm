import enum
import hashlib
import inspect
import sys
from functools import wraps
from pathlib import Path
from typing import List, Union

from cpppm import _jenv
from cpppm.project import Project
from cpppm.target import Target
from cpppm.utils import working_directory
from cpppm.utils.pathlist import PathList


class EventKind(enum.IntEnum):
    CONFIG = 0
    PRE_BUILD = 1
    POST_BUILD = 2
    GENERATOR = 3
    UPDATER = 4


class Event:
    def __init__(self, event_type: EventKind, target: Union[Target, PathList],
                 *args, depends=None, cwd=None, **kwargs):
        self.cwd = cwd
        if depends is None:
            depends = []
        self.event_type: EventKind = event_type
        self.args = args
        if not isinstance(depends, list):
            self.depends = [depends]
        else:
            self.depends = depends
        self.kwargs = kwargs
        self.target = target

    def __eq__(self, other):
        if type(other) == int:
            return other == self.event_type.value
        elif isinstance(other, str):
            return other == self.event_type.name
        else:
            return super.__eq__(other)

    @property
    def name(self):
        if isinstance(self.target, Target):
            return f'{self.target.name}.{self.func.__name__}'
        else:
            pathlist: List[Path] = self.target
            tmp = "".join([str(Path(p).name) for p in pathlist])
            sha1 = hashlib.sha1(tmp.encode()).hexdigest()
            return f'{sha1}.{self.func.__name__}'

    @property
    def sha1(self):
        return hashlib.sha1(inspect.getsource(self.func).encode('utf-8')).hexdigest()

    @property
    def function_name(self):
        return self.func.__name__

    def __str__(self):
        return f'{self.project.name}.{self.function_name}'

    @property
    def type_str(self):
        return self.event_type.name

    def __call__(self, func, *args, **kwargs):
        self.func = func
        self.source_path = Path(inspect.getfile(func))
        if self.cwd is None:
            self.cwd = self.source_path.parent
        self.project = Project.current_project
        self.event_path = Project.current_project.build_path.joinpath(f'{self.function_name}.py')

        @wraps(func)
        @working_directory(self.cwd)
        def wrapper(*args, **kwargs):
            args = [*self.args, *args]
            kwargs.update(self.kwargs)
            from . import _get_logger
            logger = _get_logger(self, self.function_name)
            logger.debug(f'firing {self.function_name} with {args}, {kwargs} ({self.sha1} at {self.cwd})')
            return func(*args, **kwargs)

        if '__cpppm_event__' in sys.argv and sys.argv[-1] == self.sha1:
            sys.exit(wrapper())

        Project.current_project.build_path.mkdir(exist_ok=True)
        if self.event_type == EventKind.GENERATOR:
            Project.current_project.generators.append(self)
        else:
            self.target.events.append(self)

        setattr(wrapper, 'event', self)
        Project.current_project.set_event(wrapper)
        return wrapper


class on_configure(Event):

    def __init__(self, target: 'cpppm.Target', *args, **kwargs):
        super().__init__(EventKind.CONFIG, target, *args, **kwargs)


class on_prebuild(Event):

    def __init__(self, target: 'cpppm.Target', *args, **kwargs):
        super().__init__(EventKind.PRE_BUILD, target, *args, **kwargs)


class on_postbuild(Event):

    def __init__(self, target: 'cpppm.Target', *args, **kwargs):
        super().__init__(EventKind.POST_BUILD, target, *args, **kwargs)


class generator(Event):

    def __init__(self, filepaths: List[Union[Path, str]], *args, depends=None, cwd=None, **kwargs):
        if depends is None:
            depends = []
        if cwd is None:
            cwd = Project.build_path
        super().__init__(EventKind.GENERATOR, PathList(cwd, filepaths), *args, depends=depends, cwd=cwd, **kwargs)

    def __str__(self):
        return super().__str__()
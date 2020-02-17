import builtins
import enum
import inspect
import os
import sys
import time
from functools import wraps
from pathlib import Path
from typing import List
import hashlib

from ..target import Target
from ..project import Project
from .. import _jenv


def check_event_sha(old_sha1, sha1_path):
    sha1_path = Path(sha1_path)
    if sha1_path.exists():
        sha1 = sha1_path.open('r').read()
        print(f"old: {old_sha1}")
        print(f"new: {sha1}")
        if sha1 and old_sha1 != sha1:
            print(f"{sha1_path}  changed")
            return False
        else:
            return True
    else:
        sha1_path.open('w').write(old_sha1)
        return False


def check_generator_sha(old_sha1, sha1_path, files):
    if check_event_sha(old_sha1, sha1_path):
        for f in files:
            f = Path(f)
            if not f.exists():
                print(f"--- File missing: {f}")
                return False
            else:
                print(f"--- Updating: {f}")
                stinfo = f.stat()
                os.utime(f.absolute(), (stinfo.st_atime, time.time()))
        return True
    else:
        return False


class EventKind(enum.IntEnum):
    CONFIG = 0
    PRE_BUILD = 1
    POST_BUILD = 2
    GENERATOR = 3
    UPDATER = 4


class Event:
    def __init__(self, event_type: EventKind, target: Target, *args, depends: List = [], **kwargs):
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

    @property
    def type_str(self):
        return self.event_type.name

    def __call__(self, func, *args, **kwargs):

        self.func = func
        self.script_path = filename = Project.root_project.build_path.joinpath(f'{self.function_name}.py')

        @wraps(func)
        def wrapper(*args, **kwargs):
            args = [*self.args, *args]
            kwargs.update(self.kwargs)
            from .. import _get_logger
            logger = _get_logger(self, self.function_name)
            logger.info(f'firing {self.function_name} with {args}, {kwargs}')
            return func(*args, **kwargs)

        Project.root_project.build_path.mkdir(exist_ok=True)
        Project.root_project.build_path.joinpath(f'__init__.py').touch(exist_ok=True)
        self.module = Project.root_project. \
            script_path.relative_to(Project.root_project.source_path).with_suffix('').name
        self.package = Project.root_project.script_path.parent.with_suffix('').name

        if self.event_type == EventKind.GENERATOR:
            template_name = 'generator.py.j2'
            Project.root_project.generators.append(self)
        else:
            template_name = 'event.py.j2'
            self.target.events.append(self)

        sha1 = self.sha1
        sha1_path = filename.absolute().with_suffix('.sha1')
        if not filename.exists() or (sha1_path.exists() and sha1_path.open('r').read() != sha1):
            files = None
            if self.event_type == EventKind.GENERATOR:
                files = [f"{Path(f).absolute()}" for f in self.target]
            filename.open('w').write(_jenv.get_template(template_name).render({
                'event': self,
                'sha1_path': sha1_path.absolute(),
                'sha1': sha1,
                'files': files
            }))
            print(f'{self.name} ----> {self.sha1}')
            if sha1_path.exists():
                sha1_path.unlink()

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

    def __init__(self, file_paths: List[Path], *args, depends=[], **kwargs):
        super().__init__(EventKind.GENERATOR, file_paths, *args, depends=depends, **kwargs)

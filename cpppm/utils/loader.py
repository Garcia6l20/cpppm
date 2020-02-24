from pathlib import Path

from cpppm import Project


def load_module(path, name=None):
    import importlib.machinery as machinery
    import uuid
    if name is None:
        name = f'{Path(path).name}-{str(uuid.uuid1())}'
    loader = machinery.SourceFileLoader(name, str(path))
    return loader.load_module()


def load_project(path=Path.cwd()) -> Project:
    return load_module(path / 'project.py').project

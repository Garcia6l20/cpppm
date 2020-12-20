import importlib
import inspect
from pathlib import Path


def instantiation_path(obj):
    return Path(inspect.getfile(inspect.getmodule(obj))).parent


def get_class_id(obj):
    module = inspect.getmodule(obj)
    module_path = inspect.getfile(module)
    return f'{module.__name__}#{module_path}#{obj.__class__.__qualname__}'


def get_class_from_id(class_id:str):
    module_name, module_path, class_name = class_id.split('#')
    module = importlib.import_module(module_name, module_path)
    splitted = class_name.split('.')
    tmp = module
    for item in splitted:
        tmp = getattr(tmp, item)
    return tmp


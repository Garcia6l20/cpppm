import os
import re
from pathlib import Path


class _Quiet:
    def success(self, *args):
        pass

    def error(self, *args):
        pass

    def info(self, *args):
        pass


def find_executables(searched_name, paths=None, regex=False, resolve=False):
    """Find executable list
    :paths: list of search paths (default: '$PATH')
    :regex: use regex for file matching"""

    if not paths:
        paths = os.getenv('PATH').split(':')

    if regex:
        def _match(name):
            return re.match(searched_name, name)
    else:
        def _match(name):
            return searched_name == name

    result = set()
    resolved_result = set()
    for path in paths:
        for root, _, files in os.walk(path):
            for filename in files:
                if _match(filename):
                    filepath = Path(root) / filename
                    filepath_resolved = filepath.resolve()
                    if filepath_resolved not in resolved_result:
                        result.add(filepath)
                        resolved_result.add(filepath_resolved)
    return resolved_result if resolve else result

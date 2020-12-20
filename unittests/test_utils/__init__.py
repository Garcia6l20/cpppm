import shutil
import tempfile
from pathlib import Path

import aiounittest
import unittest

from cpppm import cache
from cpppm.config import config
from cpppm.utils.inspect import instantiation_path


class TmpDirTestCase:

    __temp_dir = None
    temp_dir_name = None

    def setUp(self):
        test_path = Path(tempfile.gettempdir()) / f'{self.temp_dir_name or self.__class__.__name__}'
        test_path.mkdir(exist_ok=True)
        self.__temp_dir = tempfile.TemporaryDirectory(dir=test_path)

    def tearDown(self):
        self.__temp_dir.cleanup()


class BuildTestCaseBase:

    def __init__(self, *args, **kwargs):
        self.clean_cache = kwargs['clean_cache'] if 'clean_cache' in kwargs else False

    @classmethod
    def setUpClass(cls):
        test_path = Path(tempfile.gettempdir()) / f'cpppm-test-{cls.__name__}'
        test_path.mkdir(exist_ok=True)
        cls.temp_dir = tempfile.TemporaryDirectory(dir=test_path)
        config.init(instantiation_path(cls) / 'source',
                    Path(cls.temp_dir.name) / 'build')

    def setUp(self):
        if self.clean_cache:
            shutil.rmtree(cache.source_root / '.cpppm')

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()


class BuildTestCase(BuildTestCaseBase, unittest.TestCase):
    pass
    # def __init__(self, *args, **kwargs):
    #     BuildTestCaseBase.__init__(self, *args, **kwargs)
    #     unittest.TestCase.__init__(self)
    #
    #
    # def __add_error_replacement(self, _, err):
    #     value, traceback = err[1:]
    #     raise value.with_traceback(traceback)


class AsyncBuildTestCase(BuildTestCaseBase, aiounittest.AsyncTestCase):
    pass
    # def __init__(self, *args, **kwargs):
    #     super(BuildTestCaseBase, self).__init__(*args, **kwargs)
    #     super(unittest.TestCase, self).__init__()

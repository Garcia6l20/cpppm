import tempfile
import unittest
from pathlib import Path

from cpppm import Project


class ProjectBaseTestCase(unittest.TestCase):
    build_path = Path('/tmp/cpppm-tests/ProjectBaseTestCase-build')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = Project('test', build_path=ProjectBaseTestCase.build_path)
        self.test1 = self.project.library('testlib1')
        self.test2 = self.project.library('testlib2')
        self.test3 = self.project.library('testlib3')
        self.test2.link_libraries = self.test3, 'boost'
        self.exe = self.project.main_executable()
        self.exe.link_libraries = self.test1, self.test2
        self.source_path = self.exe.source_path

    def test_compile_definitions(self):
        self.test1.compile_definitions = {'DEF1': None}
        self.test2.compile_definitions = {'DEF2.1': 21, 'DEF2.2': 22}
        self.test3.compile_definitions = {'DEF3.1': 31, 'DEF3.2': 32}
        self.assertTrue(self.test1.compile_definitions == {'DEF1': None})
        self.assertTrue(self.test2.compile_definitions == {'DEF2.1': 21, 'DEF2.2': 22, 'DEF3.1': 31, 'DEF3.2': 32})
        self.assertTrue(self.test3.compile_definitions == {'DEF3.1': 31, 'DEF3.2': 32})
        self.assertTrue(
            self.exe.compile_definitions == {'DEF1': None, 'DEF2.1': 21, 'DEF2.2': 22, 'DEF3.1': 31, 'DEF3.2': 32})

    def test_include_path(self):
        self.test1.include_dirs = 'test1', 'test1_inc'
        self.test2.include_dirs = 'test2', 'test2_inc'
        self.test3.include_dirs = 'test3', 'test3_inc'
        self.assertTrue(all(str(p) in {'test1', 'test1_inc'} for p in self.test1.include_dirs))
        self.assertTrue(all(str(p) in {'test2', 'test2_inc', 'test3', 'test3_inc'} for p in self.test2.include_dirs))
        self.assertTrue(all(str(p) in {'test3', 'test3_inc'} for p in self.test3.include_dirs))
        self.assertTrue(all(str(p) in {'test1', 'test1_inc', 'test2', 'test2_inc', 'test3', 'test3_inc'}
                            for p in self.exe.include_dirs))


class MultiProjectTestCase(unittest.TestCase):
    tempdir = tempfile.TemporaryDirectory(prefix='cpppm-tests-')
    build_path = Path(tempdir.name)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = Project('test', build_path=self.build_path, source_path=self.build_path)
        self.test1 = self.project.library('testlib1')
        self.subproject1 = Project('test-sp1', build_path=self.build_path / 'sp1', source_path=self.build_path / 'sp1')
        self.project._subprojects.add(self.subproject1)
        self.subproject1.library('sp-testlib1')

        self.stand_alone_project = Project('standalone-test', build_path=self.build_path, source_path=self.build_path)
        self.stand_alone_project.library('st-testlib1')

    def test_project_libraries(self):
        self.assertTrue('testlib1' in [t.name for t in self.project.targets])
        self.assertTrue('sp-testlib1' in [t.name for t in self.project.targets])
        self.assertFalse('st-testlib1' in [t.name for t in self.project.targets])


if __name__ == '__main__':
    unittest.main()

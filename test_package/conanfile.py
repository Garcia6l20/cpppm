from conans import ConanFile, tools
from cpppm.project import load_project
from pathlib import Path
import asyncio
import sys


class conantestpackageProject(ConanFile):
    name = 'conan-test-package'
    # url = 'None'
    version = 'None'
    description = 'None'
    license = 'None'
    settings = {"os", "compiler", "build_type", "arch"}
    options = {'fPIC': [True, False], 'shared': [True, False]}
    requires = tuple({'cpppm-examples/0.0.0'})
    build_requires = tuple(set())
    default_options = {'fPIC': True, 'shared': False}
    no_copy_source = True
    exports_sources = '*', '!build/*', '!__pycache__/'

    def deploy(self):
        self.copy("*", dst="bin", src="bin")

    def configure(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    @property
    def project(self):
        if not hasattr(self, '__project__'):
            print(f'build_folder: {self.build_folder}')
            print(f'source_folder: {self.source_folder}')
            sys.path.append(self.source_folder)
            self.__project__ = load_project(Path(self.source_folder))
        return self.__project__

    def build(self):
        loop = asyncio.get_event_loop()
        self.project.install_requirements()
        loop.run_until_complete(self.project.build())

    def imports(self):
        self.copy("*", src="@bindirs", dst="bin")
        self.copy("*", src="@libdirs", dst="lib")

    def package(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.project.install(self.package_folder))

    def package_info(self):
        self.cpp_info.libs = tools.collect_libs(self)
        self.cpp_info.bindirs = ['bin']
        self.cpp_info.description = self.description

    def test(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.project.test())

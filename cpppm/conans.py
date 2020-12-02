import asyncio
from pathlib import Path

from conans import ConanFile as ConanConanFile
from conans import tools
from cpppm import Project, Library, root_project

import nest_asyncio
nest_asyncio.apply()


class PackageInfos:

    def __init__(self, data):

        self.include_dirs = set()
        self.lib_dirs = set()
        self.libs = set()
        self.res_dirs = set()
        self.bin_dirs = set()
        self.build_dirs = set()
        self.defines = dict()
        self.name = data['name']
        self.version = data['version']
        self.root = Path(data['rootpath'])
        self.description = data['description'] if 'description' in data else None
        self.load(data)
        self.header_only = self.name not in data['libs']

    def load(self, comp):
        if 'include_paths' in comp:
            self.include_dirs.update(comp['include_paths'])
        if 'lib_paths' in comp:
            self.lib_dirs.update(comp['lib_paths'])
        if 'libs' in comp:
            self.libs.update([lib for lib in comp['libs'] if lib != self.name])
        if 'system_libs' in comp:
            self.libs.update(comp['system_libs'])
        if 'res_paths' in comp:
            self.res_dirs.update(comp['res_paths'])
        if 'bin_paths' in comp:
            self.bin_dirs.update(comp['bin_paths'])
        if 'build_paths' in comp:
            self.build_dirs.update(comp['build_paths'])
        if 'defines' in comp:
            for definition in comp['defines']:
                tmp = definition.split('=')
                self.defines[tmp[0]] = tmp[1] if len(tmp) > 1 else None

    @property
    def conan_ref(self):
        return f'{self.name}/{self.version}@'


class PackageLibrary(Library):

    def __init__(self, infos, **kwargs):
        self._infos = PackageInfos(infos)
        super().__init__(self._infos.name, self._infos.root, self._infos.root, **kwargs)
        self.include_dirs = self._infos.include_dirs
        self.link_libraries = self._infos.libs
        self.compile_definitions = self._infos.defines
        self.library_dirs = {self._infos.root / p for p in self._infos.lib_dirs}

    def resolve_deps(self):
        # for dep in self._infos.deps:
        #     self.link_libraries = Project._pkg_libraries[dep]
        pass

    @property
    def conan_ref(self):
        return self._infos.conan_ref

    @property
    def is_header_only(self):
        return self._infos.header_only

    async def build(self):
        return False


class ConanFile(ConanConanFile):
    project: Project = root_project()

    name = project.package_name
    # url = project.url
    version = project.version
    license = project.license
    settings = {"os", "compiler", "build_type", "arch"}
    options = project.options
    requires = tuple(project.requires)
    build_requires = tuple(project.build_requires)
    default_options = project.default_options
    no_copy_source = False
    exports_sources = '*'

    def deploy(self):
        self.copy("*", dst="bin", src="bin")

    def configure(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def build(self):
        print(self.source_folder)
        loop = asyncio.get_event_loop()
        ConanFile.project.install_requirements()
        loop.run_until_complete(ConanFile.project.build())

    def package(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(ConanFile.project.install(self.package_folder))

    def package_info(self):
        self.cpp_info.libs = tools.collect_libs(self)
        self.cpp_info.bindirs = ['bin']

    def test(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(ConanFile.project.test())

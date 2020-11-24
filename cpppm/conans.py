import asyncio
from pathlib import Path

from conans import ConanFile as ConanConanFile
from conans import tools
from cpppm import Project, Library, root_project

import nest_asyncio
nest_asyncio.apply()


class PackageInfos:

    def __init__(self, raw):

        self.include_dirs = set()
        self.lib_dirs = set()
        self.libs = set()
        self.res_dirs = set()
        self.bin_dirs = set()
        self.build_dirs = set()
        self.defines = dict()

        self._raw = raw
        self.name = self.recipe['name']
        self._cpp_infos = dict()
        for d in self.packages:
            self._cpp_infos.update(d['cpp_info'])
        self.root = Path(self._cpp_infos['rootpath'])
        self.version = self._cpp_infos['version']
        self.description = self._cpp_infos['description']
        self.load(self._cpp_infos)
        if 'components' in self._cpp_infos:
            for comp in self._cpp_infos['components'].values():
                self.load(comp)

    @property
    def recipe(self):
        return self._raw['recipe']

    @property
    def packages(self):
        return self._raw['packages']

    @property
    def deps(self):
        return self._cpp_infos['public_deps'] if 'public_deps' in self._cpp_infos else {}

    def load(self, comp):
        if 'includedirs' in comp:
            self.include_dirs.update(comp['includedirs'])
        if 'libdirs' in comp:
            self.lib_dirs.update(comp['libdirs'])
        if 'libs' in comp:
            self.libs.update(comp['libs'])
        if 'system_libs' in comp:
            self.libs.update(comp['system_libs'])
        if 'resdirs' in comp:
            self.res_dirs.update(comp['resdirs'])
        if 'bindirs' in comp:
            self.bin_dirs.update(comp['bindirs'])
        if 'builddirs' in comp:
            self.build_dirs.update(comp['builddirs'])
        if 'defines' in comp:
            for definition in comp['defines']:
                tmp = definition.split('=')
                self.defines[tmp[0]] = tmp[1] if len(tmp) > 1 else None


class PackageLibrary(Library):

    def __init__(self, infos, **kwargs):
        self._infos = PackageInfos(infos)
        super().__init__(self._infos.name, self._infos.root, self._infos.root, **kwargs)
        self.include_dirs = self._infos.include_dirs
        self.link_libraries = self._infos.libs
        self.compile_definitions = self._infos.defines
        self.library_dirs = {self._infos.root / p for p in self._infos.lib_dirs}

    def resolve_deps(self):
        for dep in self._infos.deps:
            self.link_libraries = Project._pkg_libraries[dep]

    @property
    def is_header_only(self):
        return self.name not in self._infos.libs

    async def build(self):
        return False


class ConanFile(ConanConanFile):
    project: Project = root_project()

    name = project.package_name
    version = project.version
    license = project.license
    settings = {"os", "compiler", "build_type", "arch"}
    options = project.options
    requires = tuple(project.requires)
    build_requires = tuple(project.build_requires)
    default_options = project.default_options
    no_copy_source = True

    def deploy(self):
        self.copy("*", dst="bin", src="bin")

    def configure(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def build(self):
        loop = asyncio.new_event_loop()
        ConanFile.project.install_requirements()
        loop.run_until_complete(ConanFile.project.build())

    def package(self):
        loop = asyncio.new_event_loop()
        loop.run_until_complete(ConanFile.project.install(self.package_folder))

    def package_info(self):
        self.cpp_info.libs = tools.collect_libs(self)
        self.cpp_info.bindirs = ['bin']

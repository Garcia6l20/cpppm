from pathlib import Path

from conans import ConanFile as ConanConanFile
from conans import tools
from cpppm import Project, Library, root_project
from cpppm.utils.pathlist import PathList


class PackageInfos:
    include_dirs = set()
    lib_dirs = set()
    libs = set()
    res_dirs = set()
    bin_dirs = set()
    build_dirs = set()
    defines = set()
    version = None
    description = None
    root = None

    def __init__(self, raw):
        self._raw = raw
        self.root = Path(raw['rootpath'])
        self.version = raw['version']
        self.description = raw['description']
        self.load(raw)
        if 'components' in raw:
            for comp in raw['components'].values():
                self.load(comp)

    def load(self, comp):
        if 'includedirs' in comp:
            self.include_dirs.update(comp['includedirs'])
        if 'libdirs' in comp:
            self.lib_dirs.update(comp['libdirs'])
        if 'libs' in comp:
            self.libs.update(comp['libs'])
        if 'resdirs' in comp:
            self.res_dirs.update(comp['resdirs'])
        if 'bindirs' in comp:
            self.bin_dirs.update(comp['bindirs'])
        if 'builddirs' in comp:
            self.build_dirs.update(comp['builddirs'])
        if 'defines' in comp:
            self.defines.update(comp['defines'])


class PackageLibrary(Library):

    def __init__(self, name, infos, **kwargs):
        self._infos = PackageInfos(infos)
        super().__init__(name, self._infos.root, self._infos.root, **kwargs)

    def build(self, force=False):
        data = {
            'libraries': self._infos.libs,
            'library_paths': PathList(self._infos.root, *self._infos.lib_dirs).absolute(),
            'include_paths': PathList(self._infos.root, *self._infos.include_dirs).absolute(),
            'compile_definitions': self._infos.defines,
            'compile_options': set(),  # TODO
        }
        return data, False


class ConanFile(ConanConanFile):
    project: Project = root_project()

    name = project.package_name
    version = project.version
    license = project.license
    settings = project.settings
    options = project.options
    requires = project.requires
    build_requires = project.build_requires
    default_options = project.default_options
    no_copy_source = True

    def deploy(self):
        self.copy("*", dst="bin", src="bin")

    def configure(self):
        # tools.check_min_cppstd(self, "20")
        if self.settings.os == "Windows":
            del self.options.fPIC

    def build(self):
        ConanFile.project.install_requirements()
        ConanFile.project.generate()
        ConanFile.project.build()

    def package(self):
        ConanFile.project.install(self.package_folder)

    def package_info(self):
        self.cpp_info.libs = tools.collect_libs(self)
        self.cpp_info.bindirs = ['bin']
        self.cpp_info.build_modules.extend(ConanFile.project.dist_layout.build_modules)

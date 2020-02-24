from conans import ConanFile as ConanConanFile
from conans import tools
from cpppm import Project
from cpppm.utils.decorators import classproperty
from cpppm.utils.loader import load_project


class ConanFile(ConanConanFile):
    # project: Project = Project.root_project
    #
    # name = project.package_name
    # version = project.version
    # license = project.license
    # settings = list(project.settings.keys())
    # options = project.options
    # requires = project.requires
    # build_requires = project.build_requires
    # default_options = project.default_options
    # # no_copy_source = True

    __project: Project

    @classproperty
    def project(cls):
        if not hasattr(cls, '__project'):
            setattr(cls, '__project', load_project())
        return cls.__project

    def deploy(self):
        self.copy("*", dst="bin", src="bin")

    def configure(self):

        # tools.check_min_cppstd(self, "20")

        if self.settings.os == "Windows":
            del self.options.fPIC

    def build(self):
        self.project.generate()
        self.project.build()

    def package(self):
        self.project.install(self.package_folder)

    def package_info(self):
        self.cpp_info.libs = tools.collect_libs(self)
        self.cpp_info.bindirs = ['bin']
        self.cpp_info.build_modules.extend([str(path) for _, path in self.project.dist_converter(self.project.build_modules)])

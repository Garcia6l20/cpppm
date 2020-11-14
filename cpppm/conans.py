from conans import ConanFile as ConanConanFile
from conans import tools
from cpppm import Project


class ConanFile(ConanConanFile):
    project: Project = Project.root_project

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

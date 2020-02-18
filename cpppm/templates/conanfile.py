from conans import ConanFile, tools

from cpppm import Project

project = Project.root_project
requirements, build_requirements, options, default_options = project.collect_requirements()


class TestConan(ConanFile):
    name = project.name
    version = project.version
    license = project.license
    settings = "os", "compiler", "build_type", "arch"
    options = {"fPIC": [True, False], "shared": [True, False], **options}
    requires = requirements

    default_options = {
        "fPIC": True,
        "shared": False,
        **default_options
    }
    no_copy_source = True

    def deploy(self):
        self.copy("*", dst="bin", src="bin")

    def configure(self):
        # tools.check_min_cppstd(self, "20")
        if self.settings.os == "Windows":
            del self.options.fPIC

    def build(self):
        project.install_requirements()
        project.generate()
        project.build()

    def package(self):
        project.install(self.package_folder)

    def package_info(self):
        self.cpp_info.libs = tools.collect_libs(self)
        self.cpp_info.bindirs = ['bin']

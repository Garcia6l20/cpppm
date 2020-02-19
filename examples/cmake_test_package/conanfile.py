import os
from conans import ConanFile, CMake, tools


class XdevCoreTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "cmake_find_package_multi", "cmake"

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def imports(self):
        self.copy("xdev.cmake", "cmake", "cmake")

    def test(self):
        self.run(os.path.join("bin", "xdev-core-test-package"))

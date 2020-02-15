#!/usr/bin/env python3
from cpppm import Project, main

project = Project('conan_requires')
project.requires = 'fmt/6.1.2', 'gtest/1.10.0'
exe = project.main_executable()
exe.sources = 'src/main.cpp'
exe.link_libraries = 'fmt', 'gtest'

main()

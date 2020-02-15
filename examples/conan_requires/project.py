#!/usr/bin/env python3
from cpppm import Project, main

project = Project('conan_requires')
project.requires = 'fmt/6.1.2', 'doctest/2.3.6'
exe = project.main_executable()
exe.sources = 'src/main.cpp'
exe.link_libraries = 'fmt', 'doctest'

main()

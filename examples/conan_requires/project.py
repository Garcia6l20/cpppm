#!/usr/bin/env python3
from cpppm import Project, main

project = Project('conan-requires')
project.requires = 'spdlog/1.8.1', 'doctest/2.3.6'
exe = project.main_executable()
exe.sources = 'src/main.cpp'
exe.link_libraries = 'spdlog', 'doctest'

if __name__ == '__main__':
    main()

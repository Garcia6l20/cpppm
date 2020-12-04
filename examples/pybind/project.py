#!/usr/bin/env python3
from cpppm import Project, main

project = Project('pybind')
project.requires = 'pybind11/2.6.1'

lib = project.main_library()
lib.sources = 'binding.cpp'
lib.include_dirs = '/usr/include/python3.8'
lib.link_libraries = 'pybind11', 'python'
lib.compile_options = '-std=c++17'

if __name__ == '__main__':
    main()

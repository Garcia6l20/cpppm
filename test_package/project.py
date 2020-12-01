#!/usr/bin/env python3
from cpppm import Project, main

project = Project('conan-test-package')
project.requires = 'cpppm-examples/0.0.0'

hello = project.main_executable()
hello.sources = 'main.cpp'
hello.link_libraries = 'cpppm-examples'

if __name__ == '__main__':
    main()

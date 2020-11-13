#!/usr/bin/env python3
from cpppm import Project, main

project = Project('header-only')

lib = project.main_library()
lib.sources = 'include/header_lib/header_lib.hpp'
lib.include_dirs = 'include'

lib.tests = 'tests/simple.test.cpp', 'tests/another.test.cpp'
lib.tests_backend = 'catch2/2.13.3'

# test1 = project.executable('header-only-simple-test')
# test1.sources = 'tests/simple.test.cpp'
# test1.link_libraries = 'catch2', lib

if __name__ == '__main__':
    main()

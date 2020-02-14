#!/usr/bin/env python3
from cpppm import Project, main

project = Project('basic-project')
basic = project.library('basic')
basic.sources = {
    'include/basic.hpp',
    'src/basic.cpp'
}
basic.include_dirs = 'include'
basic.shared = False
# same effect
# basic.static = True
hello = project.main_executable()
hello.sources = 'src/main.cpp'
hello.link_libraries = basic

main()

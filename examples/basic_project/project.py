#!/usr/bin/env python3
from cpppm import Project, main

project = Project('basic-project')
basic = project.library('basic')
basic.sources = {
    'include/basic.hpp',
    'src/basic.cpp',
    'src/private.hpp'
}
basic.include_dirs = 'include'
basic.compile_definitions = {'DEF': None, 'DEFAULT_WHO': '\"cpppm\"'}
basic.shared = True
# same effect
# basic.static = True
hello = project.main_executable()
hello.sources = 'src/main.cpp'
hello.link_libraries = basic

if __name__ == '__main__':
    main()

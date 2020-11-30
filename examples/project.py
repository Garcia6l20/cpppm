#!/usr/bin/env python3

from cpppm import Project, main

project = Project('cpppm-examples', '0.0.0')

project.license = 'MIT'
# project.test_folder = 'test_package'

project.subproject('hello_cpppm')
project.subproject('conan_requires')
project.subproject('basic_project')
project.subproject('header_only')

build_events = project.subproject('build_events')

project.default_executable = build_events.default_executable

if __name__ == '__main__':
    main()

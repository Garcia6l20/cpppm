#!/usr/bin/env python3

from cpppm import Project, main
from cpppm.config import config

project = Project('cpppm-examples', '0.0.0')

project.license = 'MIT'
project.description = 'CPP Package Manager example project'
project.url = 'https://github.com/Garcia6l20/cpppm'

project.subproject('hello_cpppm')
project.subproject('conan_requires')
project.subproject('basic_project')
project.subproject('header_only')

build_events = project.subproject('build_events')

project.default_executable = build_events.default_executable

config.toolchain.cxx_flags.append('/std:c++17' if config.toolchain.name == 'msvc' else '-std=c++17')

if __name__ == '__main__':
    main()

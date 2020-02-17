#!/usr/bin/env python3
from datetime import datetime

from cpppm import Project, main
from cpppm.utils.events import generator, on_configure, on_prebuild, on_postbuild

project = Project('events')
exe = project.main_executable()
exe.sources = 'src/main.cpp'
config_header = 'config.hpp'
exe.dependencies = config_header


@generator([config_header], project)
def config_generator(project):
    print('==> config_generator config.hpp')
    open('config.hpp', 'w').write(f'''#pragma once
#define GENERATED_TIME "{datetime.utcnow()}"
#define PROJECT_NAME "{project.name}"
''')


@on_configure(exe, exe)
def configure(exe):
    print(f'==> on_configure {exe.name}')


@on_prebuild(exe, exe)
def prebuild(exe):
    print(f'==> on_prebuild  {exe.name}')


@on_postbuild(exe, exe)
def postbuild(exe):
    print(f'==> on_postbuild {exe.name}')


main()

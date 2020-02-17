#!/usr/bin/env python3
from cpppm import Project, main
from cpppm.executable import Executable
from cpppm.utils.events import generator, on_configure, on_prebuild, on_postbuild

project = Project('events')
project.requires = 'fmt/6.1.2'
project.requires_options = {'fmt:header_only': True}

gen = project.executable('gen_date')
gen.sources = 'src/generator.cpp'
gen.link_libraries = 'fmt'

exe = project.main_executable()
exe.sources = 'src/main.cpp'
config_header = 'config.hpp'
exe.dependencies = config_header


@generator([config_header], gen, depends=gen)
def config_generator(generator: Executable):
    generator.run()


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

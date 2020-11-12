#!/usr/bin/env python3
from cpppm import Project, Executable, main, events

project = Project('events')
project.requires = 'fmt/7.1.2'
project.requires_options = {'fmt:header_only': True}

gen = project.executable('gen_date')
gen.sources = 'src/generator.cpp'
gen.link_libraries = 'fmt'

exe = project.main_executable()
exe.sources = 'src/main.cpp'


@events.generator(['config.hpp'], gen, depends=gen, cwd=exe.build_path / 'include')
def config_generator(generator: Executable):
    generator.run()


exe.dependencies = config_generator


@events.on_configure(exe, exe)
def configure(exe):
    print(f'==> on_configure {exe.name}')


@events.on_prebuild(exe, exe)
def prebuild(exe):
    print(f'==> on_prebuild  {exe.name}')


@events.on_postbuild(exe, exe)
def postbuild(exe):
    print(f'==> on_postbuild {exe.name}')


if __name__ == '__main__':
    main()

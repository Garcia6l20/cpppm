#!/usr/bin/env python3
from cpppm import Project, Executable, main, events

project = Project('events')
project.requires = 'fmt/7.1.2'
# project.requires_options = {'fmt:header_only': True}

gen = project.executable('gen_date')
gen.install = False
gen.sources = 'src/generator.cpp'
gen.link_libraries = 'fmt'

exe = project.main_executable()
exe.sources = 'src/main.cpp'
exe.link_libraries = 'fmt'


@events.generator(['config.hpp'], gen, depends=gen, cwd=exe.build_path / 'generated')
def config_generator(generator: Executable):
    generator.run()


exe.dependencies = config_generator

if __name__ == '__main__':
    main()

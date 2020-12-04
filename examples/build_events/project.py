#!/usr/bin/env python3
from cpppm import Project, Executable, main, events
from cpppm.config import config

from ext_example.git import git_config_generator

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

exe.dependencies = git_config_generator(exe.build_path / 'generated' / 'git_config.hpp')


# note:
#   as we are in a coroutine context (and other builds/runs might occurs)
#   paths must be handled as absolute (os.chdir might affect all running subprocesses)
#   if something like os.chdir is required, just don't use async/await (but generator call will be bocking)
@events.generator([exe.build_path / 'generated' / 'config.hpp'], gen, depends=gen)
async def config_generator(generator: Executable):
    await generator.run(str(exe.build_path / 'generated' / 'config.hpp'))


exe.dependencies = config_generator

if __name__ == '__main__':
    main()

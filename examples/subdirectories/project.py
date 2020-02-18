#!/usr/bin/env python3
from pathlib import Path

from cpppm import Project, main
from git import Repo

project = Project('subdirectories')

ctti = Path('.deps/ctti')
if not ctti.exists():
    ctti_repo = Repo.clone_from('https://github.com/Manu343726/ctti.git', to_path=ctti)
else:
    ctti_repo = Repo(ctti)
ctti_repo.remotes.origin.pull()

exe = project.main_executable()
exe.sources = 'src/main.cpp'
exe.include_dirs = ctti / 'include'
exe.subdirs = ctti.absolute()
exe.link_libraries = 'ctti'

if __name__ == '__main__':
    main()

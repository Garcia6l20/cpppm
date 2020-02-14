#!/usr/bin/env python3
from cpppm import Project, main

project = Project('hello-cpppm')
hello = project.main_executable()
hello.sources = 'src/main.cpp'

main()

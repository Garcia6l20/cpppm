#!/usr/bin/env python3
from cpppm import Project, main

project = Project('Hellocpppm')
hello = project.executable('hello')
hello.sources = {'main.cpp'}
main()

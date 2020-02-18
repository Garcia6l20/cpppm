from cpppm import Project, main

project = Project('examples')

project.subproject('hello_cpppm')
project.subproject('conan_requires')
project.subproject('basic_project')

build_events = project.subproject('build_events')

project.default_executable = build_events.default_executable

if __name__ == '__main__':
    main()

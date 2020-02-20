from cpppm import Project, main


project = Project('cpppm-examples', '0.0.0')

project.license = 'MIT'
# project.test_folder = 'test_package'

project.subproject('hello_cpppm')
project.subproject('conan_requires')
project.subproject('basic_project')

print(project.requires)
print(project.targets)
print(project.options)
print(project.default_options)
print(project.settings)

build_events = project.subproject('build_events')

project.default_executable = build_events.default_executable

if __name__ == '__main__':
    main()

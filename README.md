# cpppm
CPP Project Manager

> Please note that I reference python as python3, python2 is dead and buried... RIP
>
## What is that
cpppm is a C/C++ project manager that focus on flexibility.

### A basic example

Consider following code:
- *main.cpp*:
```cpp
#define DOCTEST_CONFIG_IMPLEMENT_WITH_MAIN
#include <doctest/doctest.h>
#include <fmt/format.h>

TEST_CASE("cpppm loves conan") {
    CHECK(fmt::format("{1} loves {0} !!!", "conan", "cpppm") == "cpppm loves conan !!!");
}
```
- *project.py*:
```python
from cpppm import Project, main

project = Project('conan_requires')
project.requires = 'fmt/6.1.2', 'doctest/2.3.6'
exe = project.main_executable()
exe.sources = 'src/main.cpp'
exe.link_libraries = 'fmt', 'doctest'
main()
```
At this point you'll be able to run:
```bash
$ python ./project.py run conan_requires

# Build output ommitted...

[doctest] doctest version is "2.3.6"
[doctest] run with "--help" for options
===============================================================================
[doctest] test cases:      1 |      1 passed |      0 failed |      0 skipped
[doctest] assertions:      1 |      1 passed |      0 failed |
[doctest] Status: SUCCESS!
```

Check out the examples folder for more use cases.

## How it works

It is nothing more that a project file generator, with embedded conan package management.
It creates CMakeLists.txt file for you, calls the build commands and runs the target(s).

## Why should I use it

I was writing CMakeLists.txt files for decades, and I have been bored of doing:
```cmake
configure_file(my_cool_stuff_to_do.py.in my_cool_stuff_to_do.py)
find_package(PythonInterp REQUIRED)
function(my_cool_stuff_to_do)
    custom_command(${PYTHON_EXECUTABLE} my_cool_stuff_to_do.py ARGS ${ARGN})
endfunction()
...
```
And running many commands *conan*, *cmake*, *make*, *ctest*...
So, I wanted to turn the process from ~~*conan*, *cmake with __cool python stuff__*, *make*, *ctest*~~
into **cool python stuff**.

So, If you feel doing such stuff often, give it a try :kissing_heart:.

### Installation

- By cloning this repository:
```bash
git clone https://github.com/Garcia6l20/cpppm.git
cd cpppm
python setup.py install --user
```
- Available on [PyPi](https://pypi.org/project/cpppm/):
```bash
pip install --user cpppm
```

### Commands

Default commands can be listed with a regular help request:
```bash
$ ./project.py --help
Usage: project.py [OPTIONS] COMMAND [ARGS]...

Options:
  -v, --verbose                   Let me talk about me.
  -o, --out-directory TEXT        Build directory, generated files should go
                                  there.

  -c, --clean                     Remove all stuff before processing the
                                  following command.

  -s, --setting TEXT              Adds the given setting (eg.: '-s
                                  compiler=gcc -s compiler.version=9'), see: .

  -b, --build-type [Debug|Release]
                                  Build type, Debug or Release.
  --help                          Show this message and exit.

Commands:
  build                 Builds the project.
  configure             Configures CMake stuff.
  generate              Generates conan/CMake stuff.
  install               Installs targets to destination
  install-requirements  Install conan requirements.
  package               Installs targets to destination (experimental)
  run                   Runs the given TARGET with given ARGS.
  test                  Runs the unit tests.
```

### Documentation

No documentation yet...
For API, check the examples (Im trying to demonstrate all uses cases), use IDE to edit your project script (eg.: *Pycharm*).

### Features

- [x] CMakeLists.txt generation
- [x] Project compilation
- [x] Build events, generators
- [x] Conan package dependencies management
- [x] Executables invocation (automatically added to cli interface) 
- [x] Customizable (you can do anything you can do with python)
- [x] Cli customization (cou can add any `@cpppm.cli.command` that you want to add, see [click](https://click.palletsprojects.com/))
- [x] Unit testing (basic support)
- [ ] Conan package generation (almost working, needs more work)

## Contributing

Would be appreciated, no contribution guide, just [PEP-8 codding style](https://www.python.org/dev/peps/pep-0008/) and smart codding, fork/PR.

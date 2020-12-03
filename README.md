# cpppm
> CPP Project Manager

![master](https://github.com/Garcia6l20/cpppm/workflows/build-examples/badge.svg?branch=master) (master)  
![devel](https://github.com/Garcia6l20/cpppm/workflows/build-examples/badge.svg?branch=devel) (devel)

`cpppm` is a C/C++ build-system/package manager (through `conan`) that focus on flexibility.

While (most of) other build systems are jailing you into a re-invented scripting
language, `cpppm` is nothing else but a python module that provides you some
facilities to build your software.
Thus, you can do everything you are able to do with python.

The `cpppm` API semantics is close to `CMake` (eg.: *link_libraries*, *compile_options*, etc...).

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
#!/usr/bin/env python3
from cpppm import Project, main

project = Project('conan_requires')
project.requires = 'fmt/6.1.2', 'doctest/2.3.6'
exe = project.main_executable()
exe.sources = 'src/main.cpp'
exe.link_libraries = 'fmt', 'doctest'

if __name__ == '__main__':
    main()
```
At this point you'll be able to run:
```bash
$ ./project.py run conan_requires

# Build output ommitted...

[doctest] doctest version is "2.3.6"
[doctest] run with "--help" for options
===============================================================================
[doctest] test cases:      1 |      1 passed |      0 failed |      0 skipped
[doctest] assertions:      1 |      1 passed |      0 failed |
[doctest] Status: SUCCESS!
```

Check out the examples folder for more use cases.

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

  -d, --debug                     Print extra debug information.
  -c, --clean                     Remove all stuff before processing the
                                  following command.

  -C, --config TEXT               Config name to use.
  -b, --build-type [Debug|Release]
                                  Build type, Debug or Release.
  --help                          Show this message and exit.

Commands:
  build                 Builds the project.
  config                Project configuration.
  install               Installs targets to destination.
  install-requirements  Install conan requirements.
  package               Creates a conan package (experimental).
  run                   Runs the given TARGET with given ARGS.
  test                  Runs the unit tests.
```

### Conan biding

`cpppm` is tidally coupled to `conan` and can be used as is to create
packages.

When you add requirements to your project a `conanfile.py` appears side by side
with you `project.py`.
It is used to install your dependencies or to allow conan to interact with your project.

The generated `conanfile.py` might not be edited or it should be automatically re-generated.

So, regular `conan` process applies directly to your project.

```bash
cd examples
conan create .
conan upload cpppm-examples -r my_repo
```

User of your generated package should be able to use it with all build-systems
handled by conan and obviously with `cpppm` (see [test_package](./test_package)).

### Documentation

No documentation yet...
For API, check the examples (I'm trying to demonstrate all uses cases),
using a python IDE to edit your project script (eg.: *Pycharm*) helps a lot (doc and completion).

### Features

- [ ] ~~CMakeLists.txt generation~~ (no more using CMake)
- [x] Project compilation
- [x] ~~Build events~~ (useless), generators (will probably be moved into generic Targets)
- [x] Conan package dependencies management
- [x] Executables invocation (automatically added to cli interface) 
- [x] Customizable (you can do anything you can do with python)
- [x] Cli customization (cou can add any `@cpppm.cli.command` that you want to add, see [click](https://click.palletsprojects.com/))
- [x] Unit testing (basic support)
- [x] Conan package generation

## Contributing

Would be appreciated, no contribution guide, just [PEP-8 codding style](https://www.python.org/dev/peps/pep-0008/) and smart codding, fork/PR.

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
$ ./project.py -h
Usage: project.py [OPTIONS] COMMAND [ARGS]...

Options:
  -v, --verbose             Let me talk about me.
  -o, --out-directory TEXT  Build directory, generated files should go there.
  -d, --debug               Print extra debug information.
  -c, --clean               Remove all stuff before processing the following
                            command.

  -C, --config TEXT         Config name to use.
  -h, --help                Show this message and exit.

Commands:
  build        Builds the project.
  config       Project configuration command group.
  install      Installs targets to destination.
  interactive  Interactive python console with loaded project.
  run          Runs the given TARGET with given ARGS.
  shell        Interactive shell (cli commands in shell mode).
  sync         Synchronize conan package recipe (conanfile.py).
  test         Runs the unit tests.
  toolchain    Toolchain command group.
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

### Shell

An interactive shell mode is provided with `click-shell`.
To enable interactive shell, install `cpppm` interactive mode:
```bash
$ python -m pip install cpppm[interactive]
```

Then enter interactive shell:
```bash
$ ./project.py shell
Entering cpppm-examples shell...
cpppm-examples $ help
Documented commands (type help <topic>):
========================================
build   install               interactive  shell  test     
config  install-requirements  run          sync   toolchain

Undocumented commands:
======================
exit  help  quit

cpppm-examples $ build
[... some output omitted ...]
INFO:cpppm.UnixCompiler(gcc-11-x86_64):building Executable[events]
INFO:cpppm.UnixCompiler(gcc-11-x86_64):compiling main.o (Executable[events])
INFO:cpppm.UnixCompiler(gcc-11-x86_64):linking events
cpppm-examples $ run hello-cpppm
Source directory: /home/sylvain/projects/cpppm/examples
Build directory: /home/sylvain/projects/cpppm/examples/build/gcc-11-x86_64-Release
Project: cpppm-examples
INFO:cpppm.UnixCompiler(gcc-11-x86_64):using ccache
INFO:cpppm.UnixCompiler(gcc-11-x86_64):building Executable[hello-cpppm]
INFO:cpppm.UnixCompiler(gcc-11-x86_64):object /home/sylvain/projects/cpppm/examples/build/gcc-11-x86_64-Release/hello_cpppm/main.o is up-to-date
INFO:cpppm.UnixCompiler(gcc-11-x86_64):using ccache
INFO:cpppm.UnixCompiler(gcc-11-x86_64):building Executable[hello-cpppm]
INFO:cpppm.UnixCompiler(gcc-11-x86_64):object /home/sylvain/projects/cpppm/examples/build/gcc-11-x86_64-Release/hello_cpppm/main.o is up-to-date
Hello cpppm
cpppm-examples $ quit
```

### Interactive console

An interactive console mode is provided with `IPython`, but not installed automatically.
To enable interactive console, install `cpppm` interactive mode:
```bash
$ python -m pip install cpppm[interactive]
```

Then enter interactive console:
```bash
$ ./project.py interactive
Python 3.8.5 (default, Jul 28 2020, 12:59:40) 
Type 'copyright', 'credits' or 'license' for more information
IPython 7.19.0 -- An enhanced Interactive Python. Type '?' for help.

In [1]: await project.get_target('hello-cpppm').run('world')
INFO:cpppm.UnixCompiler(gcc-11-x86_64):using ccache
INFO:cpppm.UnixCompiler(gcc-11-x86_64):building Executable[hello-cpppm]
INFO:cpppm.UnixCompiler(gcc-11-x86_64):object /home/sylvain/projects/cpppm/examples/build/gcc-11-x86_64-Release/hello_cpppm/main.o is up-to-date
Hello world
Out[1]: (0, None, b'')

In [2]:
```

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

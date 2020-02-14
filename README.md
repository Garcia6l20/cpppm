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
#include <iostream>

int main(int argc, char** argv) {
    std::cout << "Hello " << argv[1] << " !\n";
    return 0;
}
```
- *project.py*:
```python
from cpppm import Project, main

project = Project('Hellocpppm')
hello = project.executable('hello')
hello.sources = {'main.cpp'}
main()
```
At this point you'll be able to run:
```bash
$ python ./project.py run hello cpppm
Hello cpppm !
```
Amazing, no ?

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

```bash
git clone https://github.com/Garcia6l20/cpppm.git
cd cpppm
python setup.py --user install
```

### Commands

Default commands can be listed with a regular help request:
```bash
$ python project.py --help
Usage: project.py [OPTIONS] COMMAND [ARGS]...

Options:
  -v, --verbose  Let me talk about me.
  --help         Show this message and exit.

Commands:
  build      Builds the project.
  configure  Configures CMake stuff.
  generate   Generates conan/CMake stuff.
  run        Runs the given TARGET with given ARGS.
  test       Runs the unit tests.
```

### Documentation

No documentation yet...
For API, check the examples (Im trying to demonstrate all uses cases), use IDE to edit your project script (eg.: *Pycharm*).

### Features

- [x] CMakeProject generation
- [x] Project compilation
- [ ] Conan package management (not yet, but soon)
- [x] Executables invocation (automatically added to cli interface) 
- [x] Customizable (you can do anything you can do with python)
- [x] Cli customization (cou can add any `@cpppm.cli.command` that you want to add, see [click](https://click.palletsprojects.com/))
- [ ] Git management (hum... not sure)

## Contributing

Would be appreciated, no contribution guide, just [PEP-8 codding style](https://www.python.org/dev/peps/pep-0008/) and smart codding, fork/PR.

# Toolchain

`cpppm` detects automatically available toolchains on first launch.

Toolchain manipulation is can be done via the `toolchain XXX` commands.

## Listing

To show available toolchains use the `toolchain list`:
```bash
./project.py toolchain list -h
Usage: project.py toolchain list [OPTIONS] [NAME] [VERSION] [ARCH]...

  Find available toolchains.

  NAME    toolchain name to search (eg.: gcc, clang).
  VERSION version to match (eg.: '>=10.1').

Options:
  -v, --verbose  Verbose toolchains
  -h, --help     Show this message and exit.
./project.py toolchain list
gcc-7.5-x86_64 (current) 
gcc-10.2-x86_64 
clang-11-x86_64 
clang-10-x86_64 
clang-12-x86_64 
gcc-9.3-x86_64 
gcc-11-x86_64
```

## Selecting

By default `cpppm` will use the first detected toolchain.
To select a specific toolchain you have to bind a toolchain id to a configuration:
```bash
./project.py toolchain list
gcc-7.5-x86_64 (current) 
gcc-10.2-x86_64 
clang-11-x86_64 
clang-10-x86_64 
clang-12-x86_64 
gcc-9.3-x86_64 
gcc-11-x86_64
# set toolchain for default configuration
./project config set toolchain=gcc-11-x86_64
./project.py toolchain list
gcc-7.5-x86_64 
gcc-10.2-x86_64 
clang-11-x86_64 
clang-10-x86_64 
clang-12-x86_64 
gcc-9.3-x86_64 
gcc-11-x86_64 (current)
```

You can add another configuration for an other toolchain:
```bash
./project -C gcc-9 config set toolchain=gcc-9.3-x86_64
./project.py toolchain list
gcc-7.5-x86_64 
gcc-10.2-x86_64 
clang-11-x86_64 
clang-10-x86_64 
clang-12-x86_64 
gcc-9.3-x86_64
gcc-11-x86_64 (current)
./project.py -C gcc-9 toolchain list
gcc-7.5-x86_64 
gcc-10.2-x86_64 
clang-11-x86_64 
clang-10-x86_64 
clang-12-x86_64 
gcc-9.3-x86_64 (current)
gcc-11-x86_64
```

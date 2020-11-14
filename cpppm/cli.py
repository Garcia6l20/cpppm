import logging
import shutil
import sys
from pathlib import Path

import click

from . import _output_dir_option, _logger
from .project import Project
from .library import Library


@click.group(invoke_without_command=True)
@click.option('--verbose', '-v', is_flag=True, help='Let me talk about me.')
@click.option(*_output_dir_option, default=None,
              help="Build directory, generated files should go there.")
@click.option("--debug", "-d", is_flag=True,
              help="Print extra useful infos, and sets CMAKE_VERBOSE_MAKEFILE.")
@click.option("--clean", "-c", is_flag=True,
              help="Remove all stuff before processing the following command.")
@click.option("--profile", "-p",
              help="Conan profile to use.")
@click.option("--setting", "-s", multiple=True,
              help="Adds the given setting (eg.: '-s compiler=gcc -s compiler.version=9'), see: .")
@click.option("--build-type", "-b", default="Release",
              type=click.Choice(['Debug', 'Release'], case_sensitive=True), help="Build type, Debug or Release.")
@click.pass_context
def cli(ctx, verbose, out_directory, debug, clean, profile, setting, build_type):
    if not Project.current_project.is_root:
        return
    if clean:
        out_directory = Path(out_directory) if out_directory else Project.root_project.build_path
        if out_directory.exists():
            shutil.rmtree(out_directory)
    Project.root_project.settings = {setting.split('=') for setting in setting}
    Project.build_type = build_type
    Project.current_project.build_path.mkdir(exist_ok=True)
    Project.set_profile(profile)
    if not Project.current_project.build_path.exists():
        raise RuntimeError('Failed to create build directory: {build_directory}')
    if verbose:
        logging.basicConfig(level=logging.INFO)
        _logger.setLevel(logging.INFO)
    if debug:
        logging.basicConfig(level=logging.DEBUG)
        _logger.setLevel(logging.DEBUG)
        Project.verbose_makefile = True

    if ctx.invoked_subcommand is None:
        ctx.invoke(run)


@cli.command('__cpppm_event__', hidden=True)
def __cpppm_event__():
    pass


@cli.command('install-requirements')
def install_requirements():
    """Install conan requirements."""
    Project.root_project.install_requirements()


@cli.command()
@click.option('--export-compile-commands', is_flag=True, default=False,
              help='export commands from CMake (can be used by clangd)')
@click.pass_context
def generate(ctx, export_compile_commands):
    """Generates conan/CMake stuff."""
    Project.export_compile_commands = export_compile_commands
    ctx.invoke(install_requirements)
    Project.root_project.generate()
    if export_compile_commands:
        Project.root_project.configure('-DCMAKE_EXPORT_COMPILE_COMMANDS=ON')


@cli.command()
@click.pass_context
def configure(ctx):
    """Configures CMake stuff."""
    ctx.invoke(generate)
    Project.root_project.configure()


@cli.command()
@click.option("--jobs", "-j", help="Number of build jobs", default=None)
@click.argument("target", required=False)
@click.pass_context
def build(ctx, jobs, target):
    """Builds the project."""
    source_dir = Path(sys.argv[0]).parent
    click.echo(f"Source directory: {str(source_dir.absolute())}")
    click.echo(f"Build directory: {str(Project.root_project.build_path.absolute())}")
    click.echo(f"Project: {Project.root_project.name}")
    ctx.invoke(configure)
    rc = Project.root_project.build(target, jobs)
    if rc != 0:
        click.echo(f'Build failed with return code: {rc}')
        exit(rc)


@cli.command()
@click.option('--no-build', '-n', is_flag=True, help='Do not build the project')
@click.argument("destination", default='dist')
@click.pass_context
def install(ctx, no_build, destination):
    """Installs targets to destination"""
    if not no_build:
        ctx.invoke(build)
    Project.root_project.install(destination)


@cli.command()
def package():
    """Installs targets to destination (experimental)"""
    Project.root_project.package()


@cli.command()
@click.argument("target", required=False)
@click.pass_context
def test(ctx, target):
    """Runs the unit tests."""
    ctx.invoke(build, target=target)
    if target:
        target = Project.root_project.target(target)
        assert isinstance(target, Library)
        target.test()
    else:
        raise NotImplementedError


def list_targets(proj):
    print(f'- {proj.name} project:')
    for target in proj.targets:
        print(f'  - {target.name:.<64}{target.__class__.__name__}')
    for _, sub in proj.subprojects.items():
        list_targets(sub)


@cli.command('targets')
def targets():
    """Lists project targets."""
    list_targets(Project._root_project)


@cli.command()
@click.argument("target")
@click.argument("args", required=False, nargs=-1, default=None)
@click.pass_context
def run(ctx, target, args):
    """Runs the given TARGET with given ARGS."""
    ctx.invoke(build, target=target)
    Project.root_project.run(target, *args)

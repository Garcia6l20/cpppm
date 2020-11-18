import logging
import shutil
import sys
from pathlib import Path

import click

from . import _output_dir_option, _logger
from .project import current_project, root_project, Project
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
    if not current_project().is_root:
        return
    if clean:
        out_directory = Path(out_directory) if out_directory else root_project().build_path
        if out_directory.exists():
            shutil.rmtree(out_directory)
    root_project().settings = {setting.split('=') for setting in setting}
    Project.build_type = build_type
    current_project().build_path.mkdir(exist_ok=True)
    Project.set_profile(profile)
    if not current_project().build_path.exists():
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
    root_project().install_requirements()


@cli.command()
@click.option('--export-compile-commands', is_flag=True, default=False,
              help='export commands from CMake (can be used by clangd)')
@click.pass_context
def generate(ctx, export_compile_commands):
    """Generates conan/CMake stuff."""
    Project.export_compile_commands = export_compile_commands
    ctx.invoke(install_requirements)
    root_project().generate()
    if export_compile_commands:
        root_project().configure('-DCMAKE_EXPORT_COMPILE_COMMANDS=ON')


@cli.command()
@click.pass_context
def configure(ctx):
    """Configures CMake stuff."""
    ctx.invoke(generate)
    root_project().configure()


@cli.command()
@click.option("--force", "-f", help="Forced build", is_flag=True)
@click.option("--jobs", "-j", help="Number of build jobs", default=None)
@click.argument("target", required=False)
@click.pass_context
def build(ctx, force, jobs, target):
    """Builds the project."""
    source_dir = Path(sys.argv[0]).parent
    click.echo(f"Source directory: {str(source_dir.absolute())}")
    click.echo(f"Build directory: {str(root_project().build_path.absolute())}")
    click.echo(f"Project: {root_project().name}")
    ctx.invoke(configure)
    rc = root_project().build(target, jobs, force)
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
    root_project().install(destination)


@cli.command()
def package():
    """Installs targets to destination (experimental)"""
    root_project().package()


@cli.command()
@click.argument("target", required=False)
@click.pass_context
def test(ctx, target):
    """Runs the unit tests."""
    ctx.invoke(build, target=target)
    if target:
        target = root_project().target(target)
        assert isinstance(target, Library)
        target.test()
    else:
        for tst in root_project().main_target.tests:
            tst.build()
            tst.run()


@cli.command()
@click.argument("target", required=False)
@click.argument("args", required=False, nargs=-1, default=None)
@click.pass_context
def run(ctx, target, args):
    """Runs the given TARGET with given ARGS."""
    ctx.invoke(build, target=target)
    root_project().run(target, *args)

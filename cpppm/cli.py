import logging
import shutil
import sys
from pathlib import Path

import click

from . import _output_dir_option
from .project import Project


@click.group(invoke_without_command=True)
@click.option('--verbose', '-v', is_flag=True, help='Let me talk about me.')
@click.option(*_output_dir_option, default=None,
              help="Build directory, generated files should go there.")
@click.option("--clean", "-c", is_flag=True,
              help="Remove all stuff before processing the following command.")
@click.option("--setting", "-s", help="Conan setting.", multiple=True)
@click.option("--build-type", "-b", default="Release",
              type=click.Choice(['Debug', 'Release'], case_sensitive=True), help="Build type, Debug or Release.")
@click.pass_context
def cli(ctx, verbose, out_directory, clean, setting, build_type):
    if clean:
        out_directory = Path(out_directory) if out_directory else Project.root_project.build_path
        if out_directory.exists():
            shutil.rmtree(out_directory)
    Project.settings = list(setting)
    Project.build_type = build_type
    if out_directory:
        Project.set_build_path(Path(out_directory))
    Project.root_project.build_path.mkdir(exist_ok=True)
    if not Project.root_project.build_path.exists():
        raise RuntimeError('Failed to create build directory: {build_directory}')
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    if ctx.invoked_subcommand is None:
        ctx.invoke(run)


@cli.command('__cpppm_event__')
def __cpppm_event__():
    pass


@cli.command('install-requirements')
def install_requirements():
    """Generates conan/CMake stuff."""
    Project.root_project.install_requirements()


@cli.command()
@click.pass_context
def generate(ctx):
    """Generates conan/CMake stuff."""
    ctx.invoke(install_requirements)
    Project.root_project.generate()


@cli.command()
@click.pass_context
def configure(ctx):
    """Configures CMake stuff."""
    ctx.invoke(generate)


@cli.command()
@click.argument("target", required=False)
@click.pass_context
def build(ctx, target):
    """Builds the project."""
    source_dir = Path(sys.argv[0]).parent
    click.echo(f"Source directory: {str(source_dir.absolute())}")
    click.echo(f"Build directory: {str(Project.root_project.build_path.absolute())}")
    click.echo(f"Project: {Project.root_project.name}")
    ctx.invoke(configure)
    rc = Project.root_project.build(target)
    if rc != 0:
        click.echo(f'Build failed with return code: {rc}')
        exit(rc)


@cli.command()
@click.pass_context
def test(ctx):
    """Runs the unit tests."""
    ctx.invoke(build)
    raise NotImplementedError


@cli.command()
@click.argument("target")
@click.argument("args", required=False, nargs=-1, default=None)
@click.pass_context
def run(ctx, target, args):
    """Runs the given TARGET with given ARGS."""
    ctx.invoke(build)
    Project.root_project.run(target, *args)

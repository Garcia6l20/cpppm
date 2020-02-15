import logging

import click
import sys
from pathlib import Path

from .project import Project


@click.group(invoke_without_command=True)
@click.option('--verbose', '-v', is_flag=True, help='Let me talk about me.')
@click.option("--build-directory", "-b", default="build-cpppm",
              help="Build directory, generated files should go there.")
@click.pass_context
def cli(ctx, verbose, build_directory):
    if build_directory:
        Project.set_build_path(Path(build_directory))
        Project.build_path.mkdir(exist_ok=True)
        if not Project.build_path.exists():
            raise RuntimeError('Failed to create build directory: {build_directory}')
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    if ctx.invoked_subcommand is None:
        ctx.invoke(run)


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
    click.echo(f"Build directory: {str(Project.build_path.absolute())}")
    click.echo(f"Project: {Project.root_project.name}")
    ctx.invoke(configure)
    Project.root_project.build(target)


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

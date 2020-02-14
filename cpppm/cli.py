import logging

import click
import sys
from pathlib import Path

from .project import Project


@click.group(invoke_without_command=True)
@click.option('--verbose', '-v', is_flag=True, help='Let me talk about me.')
@click.pass_context
def cli(ctx, verbose):
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    if ctx.invoked_subcommand is None:
        ctx.invoke(build)


@cli.command()
def generate():
    """Generates conan/CMake stuff."""
    Project.root_project.generate()


@cli.command()
@click.pass_context
def configure(ctx):
    """Configures CMake stuff."""
    ctx.invoke(generate)


@cli.command()
@click.option("--build-directory", "-b", default="build",
              help="Build directory, generated files should go there.")
@click.argument("target", required=False, default="all")
@click.pass_context
def build(ctx, build_directory, target):
    """Builds the project."""
    build_directory = Path(build_directory)
    source_dir = Path(sys.argv[0]).parent
    click.echo(f"Source directory: {str(source_dir.absolute())}")
    click.echo(f"Build directory: {str(build_directory.absolute())}")
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
@click.argument("args", required=False, nargs=-1)
@click.pass_context
def run(ctx, target, args):
    """Runs the given TARGET with given ARGS."""
    ctx.invoke(build)
    Project.root_project.run(target, args)

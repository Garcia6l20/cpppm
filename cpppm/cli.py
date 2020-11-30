import asyncio
import logging
import shutil
import sys
from pathlib import Path

import click

from . import _config_option, _logger
from .build.compiler import Compiler
from .project import current_project, root_project, Project
from .library import Library
from .toolchains import available_toolchains, _toolchain_finders

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.group(invoke_without_command=True, context_settings=CONTEXT_SETTINGS)
@click.option('--verbose', '-v', is_flag=True, help='Let me talk about me.')
@click.option('--out-directory', '-o', default=None,
              help="Build directory, generated files should go there.")
@click.option("--debug", "-d", is_flag=True,
              help="Print extra debug information.")
@click.option("--clean", "-c", is_flag=True,
              help="Remove all stuff before processing the following command.")
@click.option(*_config_option,
              help="Config name to use.", default='default')
@click.option("--build-type", "-b", default="Release",
              type=click.Choice(['Debug', 'Release'], case_sensitive=True), help="Build type, Debug or Release.")
@click.pass_context
def cli(ctx, verbose, out_directory, debug, clean, config, build_type):
    from .config import config as cpppm_config
    if not current_project().is_root:
        return
    if clean:
        out_directory = Path(out_directory) if out_directory else root_project().build_path
        if out_directory.exists():
            shutil.rmtree(out_directory)
    ctx.obj = cpppm_config

    Project.build_type = build_type
    current_project().build_path.mkdir(exist_ok=True)
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
        return ctx.invoke(run)


@cli.command('install-requirements')
async def install_requirements():
    """Install conan requirements."""
    root_project().install_requirements()


@cli.group('toolchain')
def toolchain_group():
    """Toolchain command group."""
    pass


@toolchain_group.command('names')
async def toolchain_names():
    """Show handled toolchain names."""
    for name in _toolchain_finders.keys():
        print(name)


@toolchain_group.command('list')
@click.argument('name', required=False)
@click.argument('version', required=False)
@click.argument('arch', required=False, nargs=-1)
async def toolchain_list(name, version, arch):
    """Find available toolchains.

    \b
    NAME    toolchain name to search (eg.: gcc, clang).
    VERSION version to match (eg.: '>=10.1')."""
    for toolchain in available_toolchains(name, version, arch):
        print(f'{toolchain}')


@cli.group('config')
def config_group():
    """Project configuration."""
    pass


@config_group.command('set')
@click.argument('items', nargs=-1)
@click.pass_context
async def config_set(ctx, items):
    """Modify configuration value(s)."""
    config = ctx.obj
    config.set(*items)
    config.save()


@config_group.command('doc')
@click.argument('items', nargs=-1)
@click.pass_context
async def config_doc(ctx, items):
    """Display configuration documentation."""
    config = ctx.obj
    config.doc(*items)


@config_group.command('show')
@click.argument('items', nargs=-1)
@click.pass_context
async def config_show(ctx, items):
    """Show current configuration value(s)."""
    config = ctx.obj
    config.show(*items)


@cli.command()
@click.option("--force", "-f", help="Forced build", is_flag=True)
@click.option("--jobs", "-j", help="Number of build jobs", default=None)
@click.argument("target", required=False)
@click.pass_context
async def build(ctx, force, jobs, target):
    """Builds the project."""
    source_dir = Path(sys.argv[0]).parent
    click.echo(f"Source directory: {str(source_dir.absolute())}")
    click.echo(f"Build directory: {str(root_project().build_path.absolute())}")
    click.echo(f"Project: {root_project().name}")
    Compiler.force = force
    await ctx.invoke(install_requirements)
    rc = await root_project().build(target, jobs)
    if rc != 0:
        click.echo(f'Build failed with return code: {rc}')
        exit(rc)


@cli.command()
@click.argument("destination", default='dist')
@click.pass_context
async def install(ctx, destination):
    """Installs targets to destination."""
    await ctx.invoke(build)
    await root_project().install(destination)


@cli.command()
async def package():
    """Creates a conan package (experimental)."""
    root_project().package()


@cli.command()
@click.argument("target", required=False)
@click.pass_context
async def test(ctx, target):
    """Runs the unit tests."""
    await ctx.invoke(build, target=target)
    if target:
        target = root_project().target(target)
        assert isinstance(target, Library)
        click.secho(f'Running {target} tests', fg='yellow')
        await target.test()
    else:
        tests = set()
        builds = set()
        for lib in Project.all:
            if isinstance(lib, Library):
                for tst in lib.tests:
                    builds.add(tst.build())
                    tests.add(tst)
        await asyncio.gather(*builds)
        for tst in tests:
            click.secho(f'Running {tst.name} test', fg='yellow')
            await tst.run()


@cli.command()
@click.argument("target", required=False)
@click.argument("args", required=False, nargs=-1, default=None)
@click.pass_context
async def run(ctx, target, args):
    """Runs the given TARGET with given ARGS."""
    await ctx.invoke(build, target=target)
    await root_project().run(target, *args)

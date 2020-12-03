import logging
import shutil
import sys
import traceback
from pathlib import Path

import click

from . import _config_option, _logger
from .build.compiler import Compiler
from .project import current_project, root_project, Project
from .toolchains import available_toolchains, toolchain_keys

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
@click.pass_context
def cli(ctx, verbose, out_directory, debug, clean, config):
    from .config import config as cpppm_config
    if not current_project().is_root:
        return
    if clean:
        out_directory = Path(out_directory) if out_directory else root_project().build_path
        if out_directory.exists():
            shutil.rmtree(out_directory)
    ctx.obj = cpppm_config

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
        return ctx.invoke(shell or run)


try:
    import IPython
except ImportError:
    pass

if 'IPython' in sys.modules:
    @cli.command()
    @click.pass_context
    async def interactive(ctx):
        """Interactive python console with loaded project."""
        locals().update({'project': root_project()})
        import asyncio
        import nest_asyncio
        loop = asyncio.get_event_loop()
        nest_asyncio.apply(loop)
        IPython.embed(using='asyncio')


try:
    import click_shell
except ImportError:
    pass

if 'click_shell' in sys.modules:
    @cli.command()
    @click.pass_context
    async def shell(ctx):
        """Interactive shell (cli commands in shell mode)."""

        import asyncio
        import nest_asyncio
        from functools import update_wrapper
        loop = asyncio.get_event_loop()
        nest_asyncio.apply(loop)

        def get_invoke(command):
            """
            Get the Cmd main method from the click command
            :param command: The click Command object
            :return: the do_* method for Cmd
            :rtype: function
            """

            assert isinstance(command, click.Command)

            def invoke_(self, arg):  # pylint: disable=unused-argument
                try:
                    import shlex
                    r = command.main(args=shlex.split(arg),
                                     prog_name=command.name,
                                     standalone_mode=False,
                                     parent=self.ctx)
                    if asyncio.iscoroutine(r):
                        loop.run_until_complete(r)
                except click.ClickException as e:
                    # Show the error message
                    e.show()
                except click.Abort:
                    # We got an EOF or Keyboard interrupt.  Just silence it
                    pass
                except SystemExit:
                    # Catch this an return the code instead. All of click's help commands do a sys.exit(),
                    # and that's not ideal when running in a shell.
                    pass
                except Exception as e:
                    traceback.print_exception(type(e), e, None)
                    click_shell.core.logger.warning(traceback.format_exc())

                # Always return False so the shell doesn't exit
                return False

            invoke_ = update_wrapper(invoke_, command.callback)
            invoke_.__name__ = 'do_%s' % command.name
            return invoke_

        # patch shell_core.get_invoke
        click_shell.core.get_invoke = get_invoke

        name = root_project().name
        ctx.command = cli
        sh = click_shell.make_click_shell(ctx, prompt=f'{name} $ ', intro=f'Entering {name} shell...')
        sh.cmdloop()


@cli.group('toolchain')
def toolchain_group():
    """Toolchain command group."""
    pass


@toolchain_group.command('names')
async def toolchain_names():
    """Show handled toolchain names."""
    for name in toolchain_keys():
        print(name)


@toolchain_group.command('list')
@click.option('-v', '--verbose', help='Verbose toolchains', is_flag=True)
@click.argument('name', required=False, type=click.Choice(toolchain_keys()))
@click.argument('version', required=False)
@click.argument('arch', required=False, nargs=-1)
@click.pass_context
async def toolchain_list(ctx, verbose, name, version, arch):
    """Find available toolchains.

    \b
    NAME    toolchain name to search (eg.: gcc, clang).
    VERSION version to match (eg.: '>=10.1')."""
    archs = arch if len(arch) else None
    for toolchain in available_toolchains(name, version, archs):
        current = toolchain.id == ctx.obj.toolchain.id
        click.secho(f'{toolchain.id} {"(current)" if current else ""}', fg='green' if current else None)
        if verbose:
            click.echo(toolchain.details())


@cli.group('config')
def config_group():
    """Project configuration command group."""
    pass


def _ac_get_config_keys():
    from cpppm.config import config
    return config.keys


@config_group.command('set')
@click.argument('items', nargs=-1)
@click.pass_context
async def config_set(ctx, items):
    """Modify configuration value(s)."""
    config = ctx.obj
    config.set(*items)
    config.save()


@config_group.command('doc')
@click.argument('items', nargs=-1, type=click.Choice(_ac_get_config_keys()))
@click.pass_context
async def config_doc(ctx, items):
    """Display configuration documentation."""
    config = ctx.obj
    config.doc(*items)


@config_group.command('show')
@click.argument('items', nargs=-1, type=click.Choice(_ac_get_config_keys()))
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
@click.option('-f', '--force', help='Force synchronization.', is_flag=True)
async def sync(force):
    """Synchronize conan package recipe (conanfile.py)."""
    root_project().pkg_sync(force)


@cli.command()
@click.argument("target", required=False)
@click.pass_context
async def test(ctx, target):
    """Runs the unit tests."""
    await ctx.invoke(build, target=target)
    await root_project().test(target)


@cli.command()
@click.argument("target", required=False)
@click.argument("args", required=False, nargs=-1, default=None)
@click.pass_context
async def run(ctx, target, args):
    """Runs the given TARGET with given ARGS."""
    await ctx.invoke(build, target=target)
    await root_project().run(target, *args)


@cli.command()
@click.argument("target")
@click.argument("args", required=False, nargs=-1, default=None)
@click.pass_context
async def debug(ctx, target, args):
    """Debug the given TARGET. ARGS args are passed to the configured debugger."""
    await ctx.invoke(build, target=target)
    await root_project().get_target(target).debug(*args)

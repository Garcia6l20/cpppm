import platform
from pathlib import Path

from .target import Target
from .utils import Runner


class Executable(Target):

    @property
    def binary(self) -> str:
        return self.name if platform.system() == 'Windows' else './' + self.name

    @property
    def executable_path(self) -> Path:
        return self._bin_path / self.binary

    async def run(self, *args, working_directory=None):
        await self.build()
        runner = Runner(self.executable_path, working_directory, env={'LD_LIBRARY_PATH': str(self._lib_path)})
        return await runner.run(*args)

    async def debug(self, *args):
        await self.build()
        from cpppm.config import config
        if not config.toolchain.dbg:
            raise RuntimeError(f'No debugger available for toolchain {config.toolchain.id}')
        return await Runner(config.toolchain.dbg).run(str(self.executable_path), *args)

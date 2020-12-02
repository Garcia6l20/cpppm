from pathlib import Path

from cpppm.events import generator
from cpppm.utils.runner import Runner

import asyncio


def git_config_generator(path):
    @generator([path])
    async def generate_git_config():
        path.parent.mkdir(exist_ok=True, parents=True)
        git = Runner('git')
        rc, out, _ = await git.run('describe', '--tags', '--always',
                                   stdout=asyncio.subprocess.PIPE, always_return=True)
        with open(path, 'w') as git_config:
            git_config.write(f'''#pragma once
#define GIT_VERSION "{out.decode().strip() if rc == 0 else 'unknown'}"
''')

    return generate_git_config

import os
import time
from pathlib import Path


def check_event_sha(old_sha1, sha1_path):
    sha1_path = Path(sha1_path)
    if sha1_path.exists():
        sha1 = sha1_path.open('r').read()
        if sha1 and old_sha1 != sha1:
            print(f"-- {sha1_path} changed")
            return False
        else:
            return True
    else:
        sha1_path.open('w').write(old_sha1)
        return False


def check_generator_sha(old_sha1, sha1_path, files):
    if check_event_sha(old_sha1, sha1_path):
        for f in files:
            f = Path(f)
            if not f.exists():
                print(f"-- File missing: {f}")
                return False
            else:
                print(f"-- Updating: {f}")
                stinfo = f.stat()
                os.utime(f.absolute(), (stinfo.st_atime, time.time()))
        return True
    else:
        return False

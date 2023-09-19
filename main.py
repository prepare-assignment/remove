import os.path
import shutil

from prepare_toolbox.core import get_input
from prepare_toolbox.file import get_matching_files


def remove() -> None:
    try:
        # glob(s) to match
        inputs = get_input("input")
        # ignore nonexistent files and arguments
        force = get_input("force")
        # remove directories and their contents recursively
        recursive = get_input("recursive")

        for glob in inputs:
            files = get_matching_files(glob, excluded=None, relative_to=None, recursive=recursive)
            if len(files) == 0 and not force:
                raise AssertionError(f"No files match {glob} and force is false")
            for path in files:
                if os.path.isdir(path):
                    if not recursive:
                        raise AssertionError(f"{path} is a directory and recursive if false")
                    shutil.rmtree(path)
                else:
                    os.remove(path)
    except Exception as e:
        print(e)
        exit(1)


remove()

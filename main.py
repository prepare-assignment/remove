import os.path
import shutil

from prepare_toolbox.core import get_input, set_failed, debug
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
                set_failed(f"No files matched for {glob}, but is required")
            debug(f"Glob: {glob}, matched files: {files}")
            for path in files:
                if os.path.isdir(path):
                    if not recursive:
                        set_failed(f"{path} is a directory and recursive if false")
                    shutil.rmtree(path)
                else:
                    os.remove(path)
    except Exception as e:
        set_failed(e)


remove()

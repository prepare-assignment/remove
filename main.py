import os
import shutil
from typing import List

from prepare_toolbox.core import get_input, set_failed, debug, set_output
from prepare_toolbox.file import get_matching_files


def remove() -> None:
    try:
        os.path.isfile("")
        # glob(s) to match
        inputs = get_input("input")
        # ignore nonexistent files and arguments
        force = get_input("force")
        # remove directories and their contents recursively
        recursive = get_input("recursive")

        all_files: List[str] = []

        for glob in inputs:
            files = get_matching_files(glob, excluded=None, relative_to=None, recursive=recursive)
            if len(files) == 0 and not force:
                set_failed(f"'{glob}' doesn't match any files, set 'force' to ignore")
            debug(f"Glob: {glob}, matched files: {files}")
            for path in files:
                if os.path.isdir(path):
                    if not recursive:
                        set_failed(f"Cannot remove '{path}' as it is a directory, set 'recursive' to remove")
                    shutil.rmtree(path)
                else:
                    os.remove(path)
            all_files.extend(files)
        set_output("files", all_files)
    except Exception as e:
        set_failed(e)


if __name__ == "__main__":
    remove()

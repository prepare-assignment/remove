import os
import shutil
from pathlib import PurePosixPath
from typing import Set

from prepare_toolbox.core import get_input, set_failed, debug, set_output
from prepare_toolbox.file import get_matching_files


def remove() -> None:
    try:
        # glob(s) to match
        inputs = get_input("input")
        # ignore nonexistent files and arguments
        force = get_input("force")
        # remove directories and their contents recursively
        recursive = get_input("recursive")

        # First match all globs, before anything is removed: a glob can match a directory and (another glob)
        # its contents, e.g. 'out' and 'out/**'
        matched: Set[str] = set()
        for glob in inputs:
            files = get_matching_files(glob, excluded=None, relative_to=None, recursive=recursive)
            if len(files) == 0 and not force:
                set_failed(f"'{glob}' doesn't match any files, set 'force' to ignore")
            debug(f"Glob: {glob}, matched files: {files}")
            matched.update(files)
        # Sorted: a deterministic output, and a directory comes before its contents
        all_files = sorted(matched)

        removed: Set[PurePosixPath] = set()
        for path in all_files:
            # Already removed, itself or together with a directory it is in
            posix = PurePosixPath(path)
            if posix in removed or any(parent in removed for parent in posix.parents):
                continue
            if os.path.isdir(path):
                if not recursive:
                    set_failed(f"Cannot remove '{path}' as it is a directory, set 'recursive' to remove")
                shutil.rmtree(path)
            else:
                os.remove(path)
            removed.add(posix)
        set_output("files", all_files)
    except Exception as e:
        set_failed(e)


if __name__ == "__main__":
    remove()

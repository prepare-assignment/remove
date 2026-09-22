import os
import shutil
import stat
import sys
from pathlib import PurePosixPath
from typing import Any, Callable, Set

from prepare_toolbox.core import get_input, set_failed, debug, set_output
from prepare_toolbox.file import get_matching_files


def __clear_read_only(path: str) -> None:
    """
    Make a file writable. On Windows a read-only file (e.g. the object files of a git repository) cannot be removed,
    on Linux and macOS it can. Directory permissions are never changed.
    """
    os.chmod(path, os.stat(path).st_mode | stat.S_IWRITE)


def __retry_read_only_file(function: Callable[[str], Any], path: str, error: Any) -> None:
    """Error handler for shutil.rmtree: retry removing a read-only file, other errors are raised"""
    if os.path.isdir(path) and not os.path.islink(path):
        raise error if isinstance(error, BaseException) else error[1]
    __clear_read_only(path)
    function(path)


def __remove_file(path: str) -> None:
    try:
        os.remove(path)
    except PermissionError:
        __clear_read_only(path)
        os.remove(path)


def __behind_symlink(path: PurePosixPath) -> bool:
    """
    Whether the path is inside a symbolic link to a directory (e.g. 'out/link/file' with 'out/link -> ../..').
    Removing it would remove a file of the link's target, which can be outside the working directory.
    """
    return any(os.path.islink(parent) for parent in path.parents if parent != PurePosixPath("."))


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
        # Never follow symbolic links: only a link itself is removed, not what it points to
        for path in sorted(matched):
            if __behind_symlink(PurePosixPath(path)):
                debug(f"Skipping '{path}', it is inside a symbolic link")
                matched.discard(path)
        # Sorted: a deterministic output, and a directory comes before its contents
        all_files = sorted(matched)

        removed: Set[PurePosixPath] = set()
        for path in all_files:
            # Already removed, itself or together with a directory it is in
            posix = PurePosixPath(path)
            if posix in removed or any(parent in removed for parent in posix.parents):
                continue
            if os.path.islink(path):
                # The link itself (to a file or directory), its target is not touched
                os.unlink(path)
            elif os.path.isdir(path):
                if not recursive:
                    set_failed(f"Cannot remove '{path}' as it is a directory, set 'recursive' to remove")
                if sys.version_info >= (3, 12):
                    shutil.rmtree(path, onexc=__retry_read_only_file)
                else:
                    shutil.rmtree(path, onerror=__retry_read_only_file)
            else:
                __remove_file(path)
            removed.add(posix)
        set_output("files", all_files)
    except Exception as e:
        set_failed(e)


if __name__ == "__main__":
    remove()

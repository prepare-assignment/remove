import os.path
import shutil

from prepare_toolbox.core import get_input
from prepare_toolbox.file import get_matching_files


def remove() -> None:
    try:
        inputs = get_input("input")
        force = get_input("force")
        recursive = get_input("recursive")

        for path in inputs:
            if os.path.isdir(path):
                if recursive:
                    if force:
                        shutil.rmtree(path)
                    else:
                        os.rmdir(path)
                else:
                    raise AssertionError(f"Path {path} is a directory but recursive is not set")
            else:
                files = get_matching_files(path)
                for file in files:
                    os.remove(file)

    except Exception as e:
        print(e)
        exit(1)


remove()

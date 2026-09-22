import json
import os
import stat
import sys
from pathlib import Path
from typing import Any, Dict, Iterator

import pytest
import yaml
from pytest_mock import MockerFixture

import prepare_remove.main as main
from prepare_remove.main import remove

TASK = Path(__file__).parent.parent / "task.yml"


def set_inputs(monkeypatch: pytest.MonkeyPatch, **inputs: Any) -> None:
    """
    Pass the inputs like prepare-assignment core does: as JSON in PREPARE_<NAME> environment variables,
    including the defaults from task.yml. Use the names from task.yml, with '_' for '-'.
    """
    definition: Dict[str, Any] = yaml.safe_load(TASK.read_text(encoding="utf-8"))["inputs"]
    values = {name: spec["default"] for name, spec in definition.items() if "default" in spec}
    values.update({key.replace("_", "-"): value for key, value in inputs.items()})
    for key, value in values.items():
        if value is not None:
            monkeypatch.setenv(f"PREPARE_{key.upper()}", json.dumps(value))


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """
    project
    |- a.txt
    |- b.log
    |- out
    |  |- c.txt
    |  |- sub
    |     |- d.txt
    """
    (tmp_path / "out" / "sub").mkdir(parents=True)
    for file in ["a.txt", "b.log", "out/c.txt", "out/sub/d.txt"]:
        (tmp_path / file).write_text(file)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_remove_files(project: Path, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture) -> None:
    set_inputs(monkeypatch, input=["*.txt", "*.log"])
    set_output = mocker.patch("prepare_remove.main.set_output")
    remove()
    assert not (project / "a.txt").exists()
    assert not (project / "b.log").exists()
    assert (project / "out" / "c.txt").exists()
    set_output.assert_called_once_with("files", ["a.txt", "b.log"])


def test_remove_directory_recursive(project: Path, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture) -> None:
    set_inputs(monkeypatch, input=["out"], recursive=True)
    set_output = mocker.patch("prepare_remove.main.set_output")
    remove()
    assert not (project / "out").exists()
    assert (project / "a.txt").exists()
    set_output.assert_called_once_with("files", ["out"])


def test_directory_without_recursive_fails(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    set_inputs(monkeypatch, input=["out"])
    with pytest.raises(SystemExit):
        remove()
    assert (project / "out" / "sub" / "d.txt").exists()


def test_no_match_fails(project: Path, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture) -> None:
    set_inputs(monkeypatch, input=["missing.txt"])
    failed = mocker.spy(main, "set_failed")
    with pytest.raises(SystemExit):
        remove()
    assert "'missing.txt' doesn't match any files, set 'force' to ignore" in failed.call_args.args[0]


def test_no_match_with_force(project: Path, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture) -> None:
    set_inputs(monkeypatch, input=["missing.txt", "a.txt"], force=True)
    set_output = mocker.patch("prepare_remove.main.set_output")
    remove()
    assert not (project / "a.txt").exists()
    set_output.assert_called_once_with("files", ["a.txt"])


def test_no_globs(project: Path, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture) -> None:
    set_inputs(monkeypatch, input=[])
    set_output = mocker.patch("prepare_remove.main.set_output")
    remove()
    set_output.assert_called_once_with("files", [])


def test_outside_working_directory_is_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "project").mkdir()
    (tmp_path / "outside.txt").write_text("keep")
    set_inputs(monkeypatch, input=["../outside.txt"], force=True)
    monkeypatch.chdir(tmp_path / "project")
    with pytest.raises(SystemExit):
        remove()
    assert (tmp_path / "outside.txt").exists()


@pytest.mark.parametrize("globs", [["out/**"], ["out", "out/**"], ["out/*", "out/sub/*"]])
def test_directory_and_its_contents(globs: list, project: Path, monkeypatch: pytest.MonkeyPatch,
                                    mocker: MockerFixture) -> None:
    """A directory was removed first, then removing its contents failed with 'No such file or directory'"""
    set_inputs(monkeypatch, input=globs, recursive=True)
    set_output = mocker.patch("prepare_remove.main.set_output")
    failed = mocker.patch("prepare_remove.main.set_failed")
    remove()
    failed.assert_not_called()
    assert not (project / "out" / "sub").exists()
    assert not (project / "out" / "c.txt").exists()
    assert (project / "a.txt").exists()
    set_output.assert_called_once()


def symlink(link: Path, target: str) -> None:
    try:
        link.symlink_to(target)
    except OSError:  # pragma: no cover
        pytest.skip("Creating symbolic links is not allowed (Windows without developer mode)")


@pytest.fixture
def linked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """
    tmp_path
    |- outside
    |  |- secret.txt
    |- project
       |- out
          |- a.txt
          |- dir-link -> ../../outside
          |- file-link -> ../../outside/secret.txt
    """
    (tmp_path / "outside").mkdir()
    (tmp_path / "outside" / "secret.txt").write_text("keep")
    out = tmp_path / "project" / "out"
    out.mkdir(parents=True)
    (out / "a.txt").write_text("a")
    symlink(out / "dir-link", "../../outside")
    symlink(out / "file-link", "../../outside/secret.txt")
    monkeypatch.chdir(tmp_path / "project")
    return tmp_path


@pytest.mark.parametrize("recursive", [True, False])
@pytest.mark.parametrize("link", ["out/dir-link", "out/file-link"])
def test_symlink_is_removed_not_its_target(link: str, recursive: bool, linked: Path,
                                           monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture) -> None:
    """A symbolic link to a directory failed with '[Errno None] None'"""
    set_inputs(monkeypatch, input=[link], recursive=recursive)
    set_output = mocker.patch("prepare_remove.main.set_output")
    failed = mocker.patch("prepare_remove.main.set_failed")
    remove()
    failed.assert_not_called()
    assert not (linked / "project" / link).is_symlink()
    assert (linked / "outside" / "secret.txt").read_text() == "keep"
    set_output.assert_called_once_with("files", [link])


@pytest.mark.parametrize("glob", ["out/**/*.txt", "out/dir-link/*", "out/**"])
def test_files_behind_symlink_are_not_removed(glob: str, linked: Path, monkeypatch: pytest.MonkeyPatch,
                                              mocker: MockerFixture) -> None:
    """Globs followed a symbolic link and removed its target's files, even outside the working directory"""
    set_inputs(monkeypatch, input=[glob], recursive=True, force=True)
    set_output = mocker.patch("prepare_remove.main.set_output")
    failed = mocker.patch("prepare_remove.main.set_failed")
    remove()
    failed.assert_not_called()
    assert (linked / "outside" / "secret.txt").read_text() == "keep"
    assert not any("dir-link/" in file for file in set_output.call_args.args[1])


@pytest.fixture
def read_only(project: Path) -> Iterator[Path]:
    """Read-only files, like the object files of a git repository (on Windows these can't be removed)"""
    objects = project / "repo" / ".git" / "objects"
    objects.mkdir(parents=True)
    (objects / "pack").write_text("x")
    (project / "locked.txt").write_text("x")
    os.chmod(objects / "pack", stat.S_IREAD)
    os.chmod(project / "locked.txt", stat.S_IREAD)
    yield project


def test_directory_with_read_only_files(read_only: Path, monkeypatch: pytest.MonkeyPatch,
                                        mocker: MockerFixture) -> None:
    """Failed with 'Permission denied' on Windows, e.g. for a directory with a git repository"""
    set_inputs(monkeypatch, input=["repo"], recursive=True)
    mocker.patch("prepare_remove.main.set_output")
    failed = mocker.patch("prepare_remove.main.set_failed")
    remove()
    failed.assert_not_called()
    assert not (read_only / "repo").exists()


def test_read_only_file(read_only: Path, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture) -> None:
    """Failed with 'Permission denied' on Windows"""
    set_inputs(monkeypatch, input=["locked.txt"])
    mocker.patch("prepare_remove.main.set_output")
    failed = mocker.patch("prepare_remove.main.set_failed")
    remove()
    failed.assert_not_called()
    assert not (read_only / "locked.txt").exists()


@pytest.mark.skipif(sys.platform == "win32" or os.geteuid() == 0,
                    reason="read-only directories only prevent removing their contents on Linux and macOS (not as root)")
def test_read_only_directory_is_not_changed(project: Path, monkeypatch: pytest.MonkeyPatch,
                                            mocker: MockerFixture) -> None:
    """Directory permissions are the user's responsibility: removing from a read-only directory fails, like rm -rf"""
    protected = project / "protected"
    protected.mkdir()
    (protected / "file.txt").write_text("x")
    os.chmod(protected, stat.S_IREAD | stat.S_IEXEC)
    try:
        set_inputs(monkeypatch, input=["protected/file.txt"])
        failed = mocker.patch("prepare_remove.main.set_failed")
        remove()
        failed.assert_called_once()
        assert (protected / "file.txt").exists()
        assert stat.S_IMODE(os.stat(protected).st_mode) == stat.S_IREAD | stat.S_IEXEC
    finally:
        os.chmod(protected, stat.S_IRWXU)


@pytest.fixture
def windows_read_only(mocker: MockerFixture) -> None:
    """Simulate Windows on every platform: a file without write permission can't be removed"""
    real_unlink = os.unlink

    def unlink(path: Any, *, dir_fd: Any = None) -> None:
        # shutil.rmtree removes files relative to an open directory (dir_fd)
        if not stat.S_ISDIR(os.lstat(path, dir_fd=dir_fd).st_mode) \
                and not os.stat(path, dir_fd=dir_fd).st_mode & stat.S_IWRITE:
            raise PermissionError(13, "Access is denied", str(path))
        real_unlink(path, dir_fd=dir_fd)

    mocker.patch("os.unlink", side_effect=unlink)
    mocker.patch("os.remove", side_effect=unlink)


@pytest.mark.parametrize("glob, removed", [(["repo"], "repo"), (["locked.txt"], "locked.txt")])
def test_read_only_files_simulated_windows(glob: list, removed: str, read_only: Path, windows_read_only: None,
                                           monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture) -> None:
    set_inputs(monkeypatch, input=glob, recursive=True)
    mocker.patch("prepare_remove.main.set_output")
    failed = mocker.patch("prepare_remove.main.set_failed")
    remove()
    failed.assert_not_called()
    assert not (read_only / removed).exists()

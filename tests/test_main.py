import json
from pathlib import Path
from typing import Any, Dict

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

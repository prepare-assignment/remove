import prepare_toolbox.core
import pytest

import main
from main import remove
from pytest_mock import MockerFixture


def test_no_globs(mocker: MockerFixture):
    def __get_input(key: str):
        if key == "input":
            return []
        return False
    mocker.patch('main.get_input', side_effect=__get_input)
    spy = mocker.spy(main, "set_output")
    remove()
    spy.assert_called_once_with("files", [])


def test_no_force(mocker: MockerFixture):
    def __get_input(key: str):
        if key == "input":
            return ["test"]
        return False
    mocker.patch('main.get_input', side_effect=__get_input)
    mocker.patch("main.get_matching_files", return_value=[])
    spy = mocker.spy(main, "set_failed")
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        remove()
    spy.assert_called_once()
    assert 'force' in spy.call_args.args[0]


def test_no_recursive(mocker: MockerFixture):
    def __get_input(key: str):
        if key == "input":
            return ["test"]
        return False
    mocker.patch('main.get_input', side_effect=__get_input)
    mocker.patch("main.get_matching_files", return_value=["file"])
    mocker.patch("os.path.isdir", return_value=True)
    spy = mocker.spy(main, "set_failed")
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        remove()
    spy.assert_called_once()
    assert 'recursive' in spy.call_args.args[0]


def test_successful(mocker: MockerFixture):
    def __get_input(key: str):
        if key == "input":
            return ["test"]
        return True

    def __is_dir(path: str):
        return True if path == "dir" else False
    mocker.patch('main.get_input', side_effect=__get_input)
    mocker.patch("main.get_matching_files", return_value=["file", "dir"])
    mocker.patch("os.path.isdir", side_effect=__is_dir)
    mocked_rmtree = mocker.patch("shutil.rmtree")
    mocked_remove = mocker.patch("os.remove")
    spy = mocker.spy(main, "set_output")

    remove()

    mocked_rmtree.assert_called_once()
    mocked_remove.assert_called_once()
    spy.assert_called_once_with("files", ["file", "dir"])


def test_exception(mocker: MockerFixture):
    def __get_input(key: str):
        raise Exception("Test")
    mocker.patch('main.get_input', side_effect=__get_input)
    spy = mocker.spy(main, "set_failed")
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        remove()
    spy.assert_called_once()
    assert 'Test' in str(spy.call_args.args[0])

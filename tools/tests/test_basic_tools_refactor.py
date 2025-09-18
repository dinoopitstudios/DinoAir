import os
from pathlib import Path


try:
    import src.tools.basic_tools as bt
except Exception:
    import tools.basic_tools as bt


def test_list_directory_contents_success(tmp_path: Path) -> None:
    # Setup: 2 files + 1 subdirectory
    f1 = tmp_path / "a.txt"
    f2 = tmp_path / "b.log"
    d1 = tmp_path / "subdir"
    f1.write_text("alpha", encoding="utf-8")
    f2.write_text("beta", encoding="utf-8")
    d1.mkdir()

    resp = bt.list_directory_contents(str(tmp_path))

    assert isinstance(resp, dict)
    if resp.get("success") is not True:
        raise AssertionError
    # Exact keys presence
    if "files" not in resp:
        raise AssertionError
    assert isinstance(resp["files"], list)
    if "directories" not in resp:
        raise AssertionError
    assert isinstance(resp["directories"], list)
    if "total_items" not in resp:
        raise AssertionError
    assert isinstance(resp["total_items"], int)
    if "path" not in resp:
        raise AssertionError
    assert isinstance(resp["path"], str)
    # No message key in current outward shape
    if "message" in resp:
        raise AssertionError

    file_names = {item["name"] for item in resp["files"]}
    dir_names = {item["name"] for item in resp["directories"]}
    if file_names != {"a.txt", "b.log"}:
        raise AssertionError
    if dir_names != {"subdir"}:
        raise AssertionError
    if resp["total_items"] != 3:
        raise AssertionError
    if Path(resp["path"]).resolve() != tmp_path.resolve():
        raise AssertionError


def test_list_directory_contents_error_path_not_exists() -> None:
    missing = "nonexistent_dir_12345"
    resp = bt.list_directory_contents(missing)

    if resp["success"] is not False:
        raise AssertionError
    # Exact error/message expectations
    if resp["error"] != f"Path does not exist: {missing}":
        raise AssertionError
    if resp["path"] != missing:
        raise AssertionError
    if resp["files"] != []:
        raise AssertionError
    if resp["directories"] != []:
        raise AssertionError
    if resp["total_items"] != 0:
        raise AssertionError
    # No message key in current outward shape
    if "message" in resp:
        raise AssertionError


def test_read_text_file_success(tmp_path: Path) -> None:
    p = tmp_path / "file.txt"
    content = "hello\nworld"
    p.write_text(content, encoding="utf-8")

    resp = bt.read_text_file(str(p), encoding="utf-8")

    if resp["success"] is not True:
        raise AssertionError
    if resp["content"] != content:
        raise AssertionError
    if Path(resp["file_path"]).resolve() != p.resolve():
        raise AssertionError
    if resp["size"] != p.stat().st_size:
        raise AssertionError
    # Internal _count_lines counts '\n' + 1 when content is non-empty
    if resp["lines"] != 2:
        raise AssertionError
    if resp["encoding"] != "utf-8":
        raise AssertionError
    # No message key in current outward shape
    if "message" in resp:
        raise AssertionError


def test_read_text_file_error_missing() -> None:
    missing = "missing_file_abc.txt"
    resp = bt.read_text_file(missing, encoding="utf-8")

    if resp["success"] is not False:
        raise AssertionError
    # Exact outward error mapping
    if resp["error"] != f"File does not exist: {missing}":
        raise AssertionError
    if resp["file_path"] != missing:
        raise AssertionError
    if resp["size"] != 0:
        raise AssertionError
    if resp["lines"] != 0:
        raise AssertionError
    if resp["encoding"] != "utf-8":
        raise AssertionError
    # No message key in current outward shape
    if "message" in resp:
        raise AssertionError


def test_execute_system_command_success() -> None:
    # Cross-platform command
    cmd = "cmd /c echo hello" if os.name == "nt" else "echo hello"

    resp = bt.execute_system_command(cmd)

    # Shape preserved
    for k in (
        "stdout",
        "stderr",
        "return_code",
        "command",
        "execution_time",
        "success",
    ):
        if k not in resp:
            raise AssertionError
    if resp["command"] != cmd:
        raise AssertionError
    if not (isinstance(resp["execution_time"], float) or resp["execution_time"] == 0):
        raise AssertionError
    if resp["return_code"] != 0:
        raise AssertionError
    if resp["success"] is not True:
        raise AssertionError
    if "hello" not in str(resp["stdout"]).lower():
        raise AssertionError
    # No message key in current outward shape
    if "message" in resp:
        raise AssertionError


def test_execute_system_command_error_empty() -> None:
    resp = bt.execute_system_command("")

    if resp["success"] is not False:
        raise AssertionError
    if resp["stderr"] != "Command cannot be empty":
        raise AssertionError
    if resp["error"] != "Command cannot be empty":
        raise AssertionError
    if resp["return_code"] != -1:
        raise AssertionError
    if resp["execution_time"] != 0:
        raise AssertionError


def test_create_json_data_success_and_file_write(tmp_path: Path) -> None:
    out = tmp_path / "out.json"
    data = {"a": 1, "b": "two"}

    resp = bt.create_json_data(data, str(out))

    if resp["success"] is not True:
        raise AssertionError
    assert isinstance(resp["json_string"], str)
    if not resp["json_string"]:
        raise AssertionError
    if resp["data"] != data:
        raise AssertionError
    if resp["file_written"] is not True:
        raise AssertionError
    # Path is absolute when written
    if Path(resp["file_path"]).resolve() != out.resolve():
        raise AssertionError
    assert resp["size"] == len(resp["json_string"])
    if not out.exists():
        raise AssertionError
    if out.read_text(encoding="utf-8") != resp["json_string"]:
        raise AssertionError
    # No message key in current outward shape
    if "message" in resp:
        raise AssertionError


def test_create_json_data_error_unserializable() -> None:
    # Use bytes to trigger stable TypeError message
    data = {"blob": b"bytes"}
    resp = bt.create_json_data(data)

    if resp["success"] is not False:
        raise AssertionError
    # Exact Python error message propagated
    if resp["error"] != "Object of type bytes is not JSON serializable":
        raise AssertionError
    if resp["file_written"] is not False:
        raise AssertionError
    if resp["file_path"] is not None:
        raise AssertionError
    if resp["size"] != 0:
        raise AssertionError
    # No message key in current outward shape
    if "message" in resp:
        raise AssertionError

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
    assert resp.get("success") is True
    # Exact keys presence
    assert "files" in resp
    assert isinstance(resp["files"], list)
    assert "directories" in resp
    assert isinstance(resp["directories"], list)
    assert "total_items" in resp
    assert isinstance(resp["total_items"], int)
    assert "path" in resp
    assert isinstance(resp["path"], str)
    # No message key in current outward shape
    assert "message" not in resp

    file_names = {item["name"] for item in resp["files"]}
    dir_names = {item["name"] for item in resp["directories"]}
    assert file_names == {"a.txt", "b.log"}
    assert dir_names == {"subdir"}
    assert resp["total_items"] == 3
    assert Path(resp["path"]).resolve() == tmp_path.resolve()


def test_list_directory_contents_error_path_not_exists() -> None:
    missing = "nonexistent_dir_12345"
    resp = bt.list_directory_contents(missing)

    assert resp["success"] is False
    # Exact error/message expectations
    assert resp["error"] == f"Path does not exist: {missing}"
    assert resp["path"] == missing
    assert resp["files"] == []
    assert resp["directories"] == []
    assert resp["total_items"] == 0
    # No message key in current outward shape
    assert "message" not in resp


def test_read_text_file_success(tmp_path: Path) -> None:
    p = tmp_path / "file.txt"
    content = "hello\nworld"
    p.write_text(content, encoding="utf-8")

    resp = bt.read_text_file(str(p), encoding="utf-8")

    assert resp["success"] is True
    assert resp["content"] == content
    assert Path(resp["file_path"]).resolve() == p.resolve()
    assert resp["size"] == p.stat().st_size
    # Internal _count_lines counts '\n' + 1 when content is non-empty
    assert resp["lines"] == 2
    assert resp["encoding"] == "utf-8"
    # No message key in current outward shape
    assert "message" not in resp


def test_read_text_file_error_missing() -> None:
    missing = "missing_file_abc.txt"
    resp = bt.read_text_file(missing, encoding="utf-8")

    assert resp["success"] is False
    # Exact outward error mapping
    assert resp["error"] == f"File does not exist: {missing}"
    assert resp["file_path"] == missing
    assert resp["size"] == 0
    assert resp["lines"] == 0
    assert resp["encoding"] == "utf-8"
    # No message key in current outward shape
    assert "message" not in resp


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
        assert k in resp
    assert resp["command"] == cmd
    assert isinstance(resp["execution_time"], float) or resp["execution_time"] == 0
    assert resp["return_code"] == 0
    assert resp["success"] is True
    assert "hello" in str(resp["stdout"]).lower()
    # No message key in current outward shape
    assert "message" not in resp


def test_execute_system_command_error_empty() -> None:
    resp = bt.execute_system_command("")

    assert resp["success"] is False
    assert resp["stderr"] == "Command cannot be empty"
    assert resp["error"] == "Command cannot be empty"
    assert resp["return_code"] == -1
    assert resp["execution_time"] == 0


def test_create_json_data_success_and_file_write(tmp_path: Path) -> None:
    out = tmp_path / "out.json"
    data = {"a": 1, "b": "two"}

    resp = bt.create_json_data(data, str(out))

    assert resp["success"] is True
    assert isinstance(resp["json_string"], str)
    assert resp["json_string"]
    assert resp["data"] == data
    assert resp["file_written"] is True
    # Path is absolute when written
    assert Path(resp["file_path"]).resolve() == out.resolve()
    assert resp["size"] == len(resp["json_string"])
    assert out.exists()
    assert out.read_text(encoding="utf-8") == resp["json_string"]
    # No message key in current outward shape
    assert "message" not in resp


def test_create_json_data_error_unserializable() -> None:
    # Use bytes to trigger stable TypeError message
    data = {"blob": b"bytes"}
    resp = bt.create_json_data(data)

    assert resp["success"] is False
    # Exact Python error message propagated
    assert resp["error"] == "Object of type bytes is not JSON serializable"
    assert resp["file_written"] is False
    assert resp["file_path"] is None
    assert resp["size"] == 0
    # No message key in current outward shape
    assert "message" not in resp

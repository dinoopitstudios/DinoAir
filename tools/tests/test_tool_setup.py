import ast
from pathlib import Path
import unittest


TOOLS_ROOT = Path(__file__).resolve().parent.parent


def _first_dict_assignment_keys(py_file: Path, var_name: str) -> list[str]:
    """Return string keys from the first top-level dict assigned to var_name."""
    tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        target_names = {t.id for t in node.targets if isinstance(t, ast.Name)}
        if var_name in target_names and isinstance(node.value, ast.Dict):
            return [
                k.value
                for k in node.value.keys
                if isinstance(k, ast.Constant) and isinstance(k.value, str)
            ]
    return []


def _top_level_functions(py_file: Path) -> set[str]:
    """Return names of top-level function definitions in module."""
    tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
    return {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}


def _read_inventory_text() -> str:
    return (TOOLS_ROOT / "TOOL_INVENTORY.md").read_text(encoding="utf-8")


class TestToolSetup(unittest.TestCase):
    def test_registry_counts_and_keys(self):
        """Verify total tool count and per-group counts (31 total)."""
        core_keys = _first_dict_assignment_keys(TOOLS_ROOT / "basic_tools.py", "AVAILABLE_TOOLS")
        notes_keys = _first_dict_assignment_keys(TOOLS_ROOT / "notes_tool.py", "NOTES_TOOLS")
        fs_keys = _first_dict_assignment_keys(
            TOOLS_ROOT / "file_search_tool.py", "FILE_SEARCH_TOOLS"
        )
        proj_keys = _first_dict_assignment_keys(TOOLS_ROOT / "projects_tool.py", "PROJECTS_TOOLS")

        assert set(core_keys) == {
            "add_two_numbers",
            "get_current_time",
            "list_directory_contents",
            "read_text_file",
            "execute_system_command",
            "create_json_data",
        }, f"Unexpected core tool keys: {core_keys}"

        assert len(notes_keys) == 8, f"Expected 8 notes tools, found {len(notes_keys)}"
        assert len(fs_keys) == 8, f"Expected 8 file search tools, found {len(fs_keys)}"
        assert len(proj_keys) == 9, f"Expected 9 project tools, found {len(proj_keys)}"
        assert len(core_keys) + len(notes_keys) + len(fs_keys) + len(proj_keys) == 31

    def test_registry_names_match_functions(self):
        """Each registry key should map to a function defined in its module."""
        # notes
        notes_file = TOOLS_ROOT / "notes_tool.py"
        notes_keys = set(_first_dict_assignment_keys(notes_file, "NOTES_TOOLS"))
        assert not notes_keys - _top_level_functions(notes_file), (
            "notes_tool has keys without functions"
        )

        # file search
        fs_file = TOOLS_ROOT / "file_search_tool.py"
        fs_keys = set(_first_dict_assignment_keys(fs_file, "FILE_SEARCH_TOOLS"))
        assert not fs_keys - _top_level_functions(fs_file), (
            "file_search_tool has keys without functions"
        )

        # projects
        proj_file = TOOLS_ROOT / "projects_tool.py"
        proj_keys = set(_first_dict_assignment_keys(proj_file, "PROJECTS_TOOLS"))
        assert not proj_keys - _top_level_functions(proj_file), (
            "projects_tool has keys without functions"
        )

    def test_inventory_consistency(self):
        """Ensure inventory mentions all tool names and shows 31 total badge."""
        inv = _read_inventory_text()
        assert "Total%20Tools-31" in inv or "Total Tools-31" in inv, "Inventory badge missing"

        core_keys = set(
            _first_dict_assignment_keys(TOOLS_ROOT / "basic_tools.py", "AVAILABLE_TOOLS")
        )
        notes_keys = set(_first_dict_assignment_keys(TOOLS_ROOT / "notes_tool.py", "NOTES_TOOLS"))
        fs_keys = set(
            _first_dict_assignment_keys(TOOLS_ROOT / "file_search_tool.py", "FILE_SEARCH_TOOLS")
        )
        proj_keys = set(
            _first_dict_assignment_keys(TOOLS_ROOT / "projects_tool.py", "PROJECTS_TOOLS")
        )

        for key in sorted(core_keys | notes_keys | fs_keys | proj_keys):
            assert key in inv, f"Tool name missing in TOOL_INVENTORY.md: {key}"


if __name__ == "__main__":
    unittest.main()

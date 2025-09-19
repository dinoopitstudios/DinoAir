"""
Code Assembler module for the Pseudocode Translator

This module handles the intelligent assembly of code blocks into cohesive
Python scripts, including import organization, function merging, and
consistency checks.
"""

from __future__ import annotations

import ast
import logging
import re
from collections import OrderedDict
from typing import TYPE_CHECKING, TypedDict

from .ast_cache import parse_cached
from .exceptions import AssemblyError, ErrorContext
from .models import BlockType, CodeBlock

if TYPE_CHECKING:
    from collections.abc import Iterator

    from .config import TranslatorConfig

logger = logging.getLogger(__name__)

# Formatting invariants (extracted, no behavior change)
SECTION_JOIN = "\n\n\n"
DEDENT_KEYWORDS = ("else:", "elif ", "except:", "except ", "finally:", "case ")
GLOBALS_CONSTANTS_HEADER = "# Constants"
GLOBALS_VARIABLES_HEADER = "# Global variables"
CONSTANT_ASSIGNMENT_PATTERN = r"^[A-Z_]+\s*="
IMPORT_GROUPS = (
    "standard",
    "third_party",
    "local",
)  # documentation/reference only; not required by any loop yet


class CodeSections(TypedDict):
    """
    Type definition for organized code sections returned by _organize_code_sections.

    Attributes:
        module_docstring: Optional module-level docstring
        functions: List of function definition code strings
        classes: List of class definition code strings
        globals: List of global variable assignment code strings
        main: List of main execution code strings
    """

    module_docstring: str | None
    functions: list[str]
    classes: list[str]
    globals: list[str]
    main: list[str]


class CodeAssembler:
    """
    Intelligently combines code segments into complete Python scripts.

    This class handles the assembly of parsed code blocks into cohesive Python
    scripts with proper import organization, function merging, and consistency
    checks. It maintains code structure while ensuring valid Python syntax.
    """

    def __init__(self, config: TranslatorConfig) -> None:
        """
        Initialize the Code Assembler.

        Args:
            config: Translator configuration object containing assembly preferences
                   including indentation, line length, and import behavior.
        """
        self.config: TranslatorConfig = config
        self.indent_size: int = config.indent_size
        self.max_line_length: int = config.max_line_length
        self.preserve_comments: bool = config.preserve_comments
        self.preserve_docstrings: bool = config.preserve_docstrings
        self.auto_import_common: bool = config.auto_import_common

        # Common imports that might be auto-added
        self.common_imports: dict[str, list[str]] = {
            "math": ["sin", "cos", "sqrt", "pi", "tan", "log", "exp"],
            "os": ["path", "getcwd", "listdir", "mkdir", "remove"],
            "sys": ["argv", "exit", "path", "platform"],
            "datetime": ["datetime", "date", "time", "timedelta"],
            "json": ["dumps", "loads", "dump", "load"],
            "re": ["match", "search", "findall", "sub", "compile"],
            "typing": ["List", "Dict", "Tuple", "Optional", "Union", "Any"],
        }

    def _extract_sections(self, blocks: list[CodeBlock]) -> list[CodeBlock]:
        """
        Parse input into Python blocks with identical logging and error semantics to the original assemble() filtering step.

        Args:
            blocks: List of code blocks to filter for Python content.

        Returns:
            List of Python code blocks, excluding other block types.

        Raises:
            AssemblyError: If filtering fails due to unexpected errors.
        """
        try:
            python_blocks = [b for b in blocks if b.type == BlockType.PYTHON]

            # comment_blocks for future use
            # comment_blocks for future use
            # comment_blocks = [
            #     b for b in blocks if b.type == BlockType.COMMENT
            # ]

            if not python_blocks:
                logger.warning("No Python blocks to assemble")
                error = AssemblyError(
                    "No Python code blocks found to assemble",
                    blocks_info=[{"type": b.type.value,
                                  "lines": b.line_numbers} for b in blocks],
                    assembly_stage="filtering",
                )
                error.add_suggestion(
                    "Ensure pseudocode was translated to Python")
                error.add_suggestion(
                    "Check that block types are correctly identified")
                logger.warning(error.format_error())
                return []
            return python_blocks
        except Exception as e:
            error = AssemblyError(
                "Failed to filter code blocks", assembly_stage="filtering", cause=e
            )
            raise error from e

    def _collect_imports(self, python_blocks: list[CodeBlock]) -> str:
        """
        Derive import statements deterministically from sections. Preserves original error messages and suggestions.

        Args:
            python_blocks: List of Python code blocks to extract imports from.

        Returns:
            Organized import section as a string.

        Raises:
            AssemblyError: If import organization fails.
        """
        try:
            return self._organize_imports(python_blocks)
        except Exception as e:
            error = AssemblyError(
                "Failed to organize imports", assembly_stage="imports", cause=e)
            error.add_suggestion("Check import statement syntax")
            error.add_suggestion("Verify module names are valid")
            raise error from e

    def _normalize_sections(self, python_blocks: list[CodeBlock]) -> CodeSections:
        """
        Trim/clean sections and resolve ordering rules by delegating to _organize_code_sections().

        Args:
            python_blocks: List of Python code blocks to organize into sections.

        Returns:
            Organized code sections with proper structure and typing.

        Raises:
            AssemblyError: If code section organization fails.
        """
        try:
            return self._organize_code_sections(python_blocks)
        except Exception as e:
            error = AssemblyError(
                "Failed to organize code sections", assembly_stage="sections", cause=e
            )
            error.add_suggestion("Check code block structure")
            error.add_suggestion("Ensure valid Python syntax in all blocks")
            raise error from e

    def _merge_definitions_with_errors(
        self, functions: list[str], classes: list[str]
    ) -> tuple[str, str]:
        """
        Wrap _merge_functions and _merge_classes with identical error handling used in _stitch_sections.
        """
        try:
            merged_functions = self._merge_functions(functions)
            merged_classes = self._merge_classes(classes)
        except Exception as e:
            error = AssemblyError(
                "Failed to merge functions and classes",
                assembly_stage="merging",
                cause=e,
            )
            error.add_suggestion("Check for naming conflicts")
            error.add_suggestion("Ensure function/class definitions are valid")
            raise error from e
        return merged_functions, merged_classes

    def _organize_globals_with_errors(self, globals_list: list[str]) -> str:
        """
        Wrap _organize_globals with identical error capture/re-raise semantics.
        """
        try:
            return self._organize_globals(globals_list)
        except Exception as e:
            error = AssemblyError(
                "Failed to organize global variables", assembly_stage="globals", cause=e
            )
            raise error from e

    def _organize_main_with_errors(self, main_list: list[str]) -> str:
        """
        Wrap _organize_main_code with identical error capture/re-raise semantics.
        """
        try:
            return self._organize_main_code(main_list)
        except Exception as e:
            error = AssemblyError(
                "Failed to organize main execution code", assembly_stage="main", cause=e
            )
            raise error from e

    def _collect_final_sections(
        self,
        module_doc: str | None,
        imports_section: str,
        globals_section: str,
        merged_functions: str,
        merged_classes: str,
        main_section: str,
    ) -> list[str]:
        """
        Build and return list of non-empty sections in exact order: module docstring, imports, globals, functions, classes, main.
        """
        final_sections: list[str] = []
        if isinstance(module_doc, str) and module_doc:
            final_sections.append(module_doc)
        if imports_section:
            final_sections.append(imports_section)
        if globals_section:
            final_sections.append(globals_section)
        if merged_functions:
            final_sections.append(merged_functions)
        if merged_classes:
            final_sections.append(merged_classes)
        if main_section:
            final_sections.append(main_section)
        return final_sections

    def _join_sections(self, sections: list[str]) -> str:
        """
        Join sections using the module-level SECTION_JOIN.
        """
        return SECTION_JOIN.join(sections)

    def _stitch_sections(self, sections: CodeSections, imports_section: str) -> str:
        """
        Build the final code string/buffer in the same order as before.
        Handles merging, globals/main organization, and section joining.

        Args:
            sections: Organized code sections with proper structure.
            imports_section: Formatted import statements.

        Returns:
            Complete assembled code as a string.

        Raises:
            AssemblyError: If any step of the stitching process fails.
        """
        # Step 3: Merge functions and classes
        merged_functions, merged_classes = self._merge_definitions_with_errors(
            sections["functions"], sections["classes"]
        )

        # Step 4: Organize global variables and constants
        globals_section = self._organize_globals_with_errors(
            sections["globals"])

        # Step 5: Organize main execution code
        main_section = self._organize_main_with_errors(sections["main"])

        # Step 7: Assemble final code
        module_docstring = sections.get("module_docstring")
        sections_list = self._collect_final_sections(
            module_docstring,
            imports_section,
            globals_section,
            merged_functions,
            merged_classes,
            main_section,
        )
        return self._join_sections(sections_list)

    def _postprocess_output(self, code: str) -> str:
        """
        Final whitespace/format touches identical to prior behavior:
        delegates to _ensure_consistency() then _final_cleanup() with the same error semantics.

        Args:
            code: Assembled code requiring final processing.

        Returns:
            Final processed code with consistent formatting.

        Raises:
            AssemblyError: If consistency checks or cleanup fails.
        """
        # Step 8: Ensure consistency
        try:
            final_code = self._ensure_consistency(code)
        except Exception as e:
            error = AssemblyError(
                "Failed to ensure code consistency",
                assembly_stage="consistency",
                cause=e,
            )
            error.add_suggestion("Check indentation throughout the code")
            error.add_suggestion("Verify consistent coding style")
            raise error from e

        # Step 9: Final validation and cleanup
        try:
            final_code = self._final_cleanup(final_code)
        except Exception as e:
            error = AssemblyError(
                "Failed during final cleanup", assembly_stage="cleanup", cause=e)
            raise error from e

        return final_code

    def assemble(self, blocks: list[CodeBlock]) -> str:
        """
        Combines segments while handling:
        - Import deduplication
        - Variable scope resolution
        - Function organization
        - Proper indentation

        Args:
            blocks: List of processed code blocks to assemble into complete Python code.

        Returns:
            Complete assembled Python code as a string, ready for execution.
            Returns empty string if no valid Python blocks are provided.

        Raises:
            AssemblyError: If any step of the assembly process fails.
        """
        # Guard invalid inputs early
        if not blocks:
            return ""

        logger.info("Assembling %d code blocks", len(blocks))

        # extract → normalize → collect imports → stitch → postprocess
        python_blocks = self._extract_sections(blocks)
        if not python_blocks:
            # Prior behavior: warn (already logged) and return empty string
            return ""

        imports_section = self._collect_imports(python_blocks)
        main_code_sections = self._normalize_sections(python_blocks)
        assembled_code = self._stitch_sections(
            main_code_sections, imports_section)
        final_code = self._postprocess_output(assembled_code)

        logger.info("Code assembly complete")
        return final_code

    def assemble_streaming(self, block_iterator: Iterator[CodeBlock]) -> str:
        """
        Assemble code from a streaming iterator of blocks.

        Args:
            block_iterator: Iterator yielding CodeBlock objects to be assembled.

        Returns:
            Complete assembled Python code as a string.

        Raises:
            AssemblyError: If assembly of collected blocks fails.
        """
        # Collect blocks from iterator
        blocks = list(block_iterator)

        # Use regular assemble method
        return self.assemble(blocks)

    # --- Incremental assembly helpers (private; used only by assemble_incremental) ---

    def _scan_existing_symbols(self, tree: ast.AST) -> tuple[set[str], set[str], set[str]]:
        existing_imports: set[str] = set()
        existing_functions: set[str] = set()
        existing_classes: set[str] = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    existing_imports.add(f"import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    existing_imports.add(f"from {module} import {alias.name}")
            elif isinstance(node, ast.FunctionDef):
                existing_functions.add(node.name)
            elif isinstance(node, ast.ClassDef):
                existing_classes.add(node.name)

        return existing_imports, existing_functions, existing_classes

    def _build_incremental_context(
        self,
        existing_imports: set[str],
        existing_functions: set[str],
        existing_classes: set[str],
    ) -> dict[str, set[str]]:
        return {
            "existing_imports": existing_imports,
            "existing_functions": existing_functions,
            "existing_classes": existing_classes,
        }

    def _should_include_function(self, code: str, existing_functions: set[str]) -> bool:
        return self._should_include_named_def(code, existing_functions, ast.FunctionDef)

    def _should_include_class(self, code: str, existing_classes: set[str]) -> bool:
        return self._should_include_named_def(code, existing_classes, ast.ClassDef)

    def _should_include_named_def(
        self,
        code: str,
        existing_names: set[str],
        expected_node: type,
    ) -> bool:
        """
        Include code if its first top-level definition name (matching expected_node)
        is not already present. On parse errors or if the name can't be determined,
        include by default to preserve previous behavior.
        """
        try:
            tree = parse_cached(code)
            name = self._first_named_node(tree, expected_node)
            return name not in existing_names if name else True
        except (SyntaxError, ValueError, TypeError):
            return True

    def _inc_prepare_context(self, previous_code: str) -> dict[str, set[str]] | None:
        """
        Prepare incremental assembly context by parsing existing code to collect:
        - existing_imports: set of 'import x' and 'from y import z' lines
        - existing_functions: set of function names
        - existing_classes: set of class names

        Args:
            previous_code: Previously assembled code to analyze for context.

        Returns:
            Dictionary containing sets of existing imports, functions, and classes.
            Returns None if previous_code cannot be parsed (SyntaxError), matching
            the original fallback behavior.
        """
        try:
            tree = parse_cached(previous_code)

            existing_imports, existing_functions, existing_classes = self._scan_existing_symbols(
                tree
            )

            return self._build_incremental_context(
                existing_imports, existing_functions, existing_classes
            )
        except SyntaxError:
            return None

    def _inc_filter_python_blocks(self, new_blocks: list[CodeBlock]) -> list[CodeBlock]:
        """
        Filter only Python blocks from new blocks.

        Args:
            new_blocks: List of new code blocks to filter.

        Returns:
            List containing only Python code blocks.
        """
        return [b for b in new_blocks if b.type == BlockType.PYTHON]

    def _inc_compute_unique_imports(
        self, python_blocks: list[CodeBlock], existing_imports: set[str]
    ) -> list[str]:
        """
        Compute import lines from new python blocks that are not already present in existing_imports.
        Preserves original import organization and filtering semantics.

        Args:
            python_blocks: List of Python code blocks to extract imports from.
            existing_imports: Set of import statements already present in previous code.

        Returns:
            List of unique import statements not already present.
        """
        new_imports = self._organize_imports(python_blocks)
        import_lines = new_imports.splitlines()
        unique_imports: list[str] = []
        for line in import_lines:
            if line.strip() and line.strip() not in existing_imports:
                # Append the original line to preserve spacing as produced by _organize_imports
                unique_imports.append(line)
        return unique_imports

    def _inc_filter_new_definitions(
        self,
        sections: CodeSections,
        existing_functions: set[str],
        existing_classes: set[str],
    ) -> tuple[list[str], list[str]]:
        """
        Filter out functions/classes from sections that already exist by name in previous code.
        Includes items on parse errors to preserve prior behavior.

        Args:
            sections: Organized code sections containing functions and classes.
            existing_functions: Set of function names already present.
            existing_classes: Set of class names already present.

        Returns:
            Tuple of (filtered_functions, filtered_classes) containing only new definitions.
        """
        filtered_functions: list[str] = []
        for func_code in sections["functions"]:
            if self._should_include_function(func_code, existing_functions):
                filtered_functions.append(func_code)

        filtered_classes: list[str] = []
        for class_code in sections["classes"]:
            if self._should_include_class(class_code, existing_classes):
                filtered_classes.append(class_code)

        return filtered_functions, filtered_classes

    def _inc_build_incremental_parts(
        self,
        unique_imports: list[str],
        filtered_functions: list[str],
        filtered_classes: list[str],
        main_sections: list[str],
    ) -> list[str]:
        """
        Build the list of incremental code parts in the same order as before.

        Args:
            unique_imports: List of unique import statements to add.
            filtered_functions: List of new function definitions.
            filtered_classes: List of new class definitions.
            main_sections: List of main execution code sections.

        Returns:
            List of code parts ready for assembly, in proper order.
        """
        incremental_parts: list[str] = []
        if unique_imports:
            incremental_parts.append("\n".join(unique_imports))
        if filtered_functions:
            incremental_parts.append("\n\n".join(filtered_functions))
        if filtered_classes:
            incremental_parts.append("\n\n".join(filtered_classes))
        if main_sections:
            incremental_parts.append("\n\n".join(main_sections))
        return incremental_parts

    def assemble_incremental(self, previous_code: str, new_blocks: list[CodeBlock]) -> str:
        """
        Incrementally assemble code by adding new blocks to existing code.

        Args:
            previous_code: Previously assembled code to extend.
            new_blocks: New blocks to add to the existing code.

        Returns:
            Updated assembled code with new blocks integrated.
            If new_blocks is empty, returns previous_code unchanged.
            If previous_code is empty, performs full assembly of new_blocks.
        """
        # Guard invalid inputs first
        if not new_blocks:
            return previous_code

        if not previous_code:
            return self.assemble(new_blocks)

        # Prepare context from previous code; on parse failure, append assembled new code
        context = self._inc_prepare_context(previous_code)
        if context is None:
            new_code = self.assemble(new_blocks)
            return f"{previous_code}\n\n{new_code}"

        # Filter to Python blocks
        python_blocks = self._inc_filter_python_blocks(new_blocks)

        # Compute imports unique to new content
        unique_imports = self._inc_compute_unique_imports(
            python_blocks, context["existing_imports"]
        )

        # Organize new non-import code into sections
        new_code_sections = self._organize_code_sections(python_blocks)

        # Filter out duplicate functions/classes by name
        filtered_functions, filtered_classes = self._inc_filter_new_definitions(
            new_code_sections,
            context["existing_functions"],
            context["existing_classes"],
        )

        # Build incremental parts and finalize
        incremental_parts = self._inc_build_incremental_parts(
            unique_imports,
            filtered_functions,
            filtered_classes,
            new_code_sections["main"],
        )

        if not incremental_parts:
            return previous_code

        incremental_code = "\n\n".join(incremental_parts)
        return f"{previous_code}\n\n{incremental_code}"

    def _accumulate_import_node(self, names: list[ast.alias], imports: dict[str, set[str]]) -> None:
        """
        For an ast.Import node’s aliases, categorize each alias.name via self._categorize_import
        and add to imports[category]. Preserves original loop ordering and semantics.
        """
        for alias in names:
            import_name = alias.name
            category = self._categorize_import(import_name)
            imports[category].add(import_name)

    def _accumulate_from_import_node(
        self, node: ast.ImportFrom, from_imports: dict[str, dict[str, set[str]]]
    ) -> None:
        """
        For an ast.ImportFrom node, normalize module to "" when None, categorize via self._categorize_import,
        and add each alias.name into from_imports[category][module]. Uses setdefault identical to existing code.
        """
        module = node.module or ""
        category = self._categorize_import(module)
        for alias in node.names:
            from_imports[category].setdefault(module, set()).add(alias.name)

    def _log_import_syntax_error(self, block: CodeBlock, e: SyntaxError) -> None:
        """
        Log SyntaxError while parsing a block for imports, replicating existing warnings and ErrorContext usage.
        """
        logger.warning("Could not parse block for imports: %s",
                       block.line_numbers)
        context = ErrorContext(
            line_number=block.line_numbers[0],
            code_snippet=block.content[:100],
            metadata={"error": str(e)},
        )
        error = AssemblyError(
            "Invalid syntax in code block",
            assembly_stage="imports",
            context=context,
        )
        error.add_suggestion("Fix syntax errors before assembly")
        logger.warning(error.format_error())

    def _accumulate_block_imports(
        self,
        block: CodeBlock,
        imports: dict[str, set[str]],
        from_imports: dict[str, dict[str, set[str]]],
    ) -> None:
        """
        Parse a single block and accumulate its imports into the provided buckets.
        Preserves original SyntaxError logging and error context behavior.

        Args:
            block: Code block to parse for import statements.
            imports: Dictionary to accumulate plain import statements by category.
            from_imports: Dictionary to accumulate from-import statements by category and module.
        """
        try:
            tree = parse_cached(block.content)

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    self._accumulate_import_node(node.names, imports)

                elif isinstance(node, ast.ImportFrom):
                    self._accumulate_from_import_node(node, from_imports)

        except SyntaxError as e:
            self._log_import_syntax_error(block, e)

    def _build_group_lines(
        self,
        category: str,
        imports: dict[str, set[str]],
        from_imports: dict[str, dict[str, set[str]]],
    ) -> list[str]:
        """
        Convert a category's imports into formatted lines with deterministic ordering.

        Args:
            category: Import category ('standard', 'third_party', or 'local').
            imports: Plain imports organized by category.
            from_imports: From-imports organized by category and module.

        Returns:
            List of formatted import lines for the specified category.
        """
        lines: list[str] = []

        # Plain imports
        if imports[category]:
            for imp in sorted(imports[category]):
                lines.append(f"import {imp}")

        # From-imports
        if from_imports[category]:
            for module, names in sorted(from_imports[category].items()):
                if names:
                    names_str = ", ".join(sorted(names))
                    lines.append(f"from {module} import {names_str}")

        return lines

    def _init_import_buckets(
        self,
    ) -> tuple[dict[str, set[str]], dict[str, dict[str, set[str]]]]:
        imports: dict[str, set[str]] = {
            "standard": set(),
            "third_party": set(),
            "local": set(),
        }
        from_imports: dict[str, dict[str, set[str]]] = {
            "standard": {},
            "third_party": {},
            "local": {},
        }
        return imports, from_imports

    def _extract_imports_from_blocks(
        self,
        blocks: list[CodeBlock],
        imports: dict[str, set[str]],
        from_imports: dict[str, dict[str, set[str]]],
    ) -> None:
        for block in blocks:
            self._accumulate_block_imports(block, imports, from_imports)

    def _append_group(
        self, import_lines: list[str], group_lines: list[str], add_trailing_blank: bool
    ) -> None:
        if group_lines:
            import_lines.extend(group_lines)
            if add_trailing_blank:
                import_lines.append("")

    def _trim_trailing_blanks(self, lines: list[str]) -> None:
        while lines and lines[-1] == "":
            lines.pop()

    def _organize_imports(self, blocks: list[CodeBlock]) -> str:
        """
        Organize and deduplicate imports from all blocks.

        Args:
            blocks: List of Python code blocks to extract and organize imports from.

        Returns:
            Organized import section as a formatted string with proper grouping
            and blank line separation between standard, third-party, and local imports.
        """
        # Initialize buckets with explicit typing
        imports, from_imports = self._init_import_buckets()

        # Extract imports from each block with preserved error/logging semantics
        self._extract_imports_from_blocks(blocks, imports, from_imports)

        # Auto-add common imports if configured (preserves existing behavior)
        if self.auto_import_common:
            self._add_common_imports(blocks, imports, from_imports)

        # Build import section with group ordering and blank-line rules preserved
        import_lines: list[str] = []

        standard_group_lines = self._build_group_lines(
            "standard", imports, from_imports)
        self._append_group(import_lines, standard_group_lines,
                           add_trailing_blank=True)

        third_party_group_lines = self._build_group_lines(
            "third_party", imports, from_imports)
        self._append_group(
            import_lines, third_party_group_lines, add_trailing_blank=True)

        local_group_lines = self._build_group_lines(
            "local", imports, from_imports)
        self._append_group(import_lines, local_group_lines,
                           add_trailing_blank=False)

        # Remove trailing empty lines (exact prior behavior)
        self._trim_trailing_blanks(import_lines)

        return "\n".join(import_lines)

    def _init_section_buckets(self) -> CodeSections:
        """
        Initialize empty code sections with proper structure.

        Returns:
            CodeSections dictionary with all sections initialized to empty state.
        """
        return {
            "module_docstring": None,
            "functions": [],
            "classes": [],
            "globals": [],
            "main": [],
        }

    def _maybe_set_module_docstring(self, tree: ast.Module, sections: CodeSections) -> None:
        """
        Extract and set module docstring if present and not already set.

        Args:
            tree: Parsed AST module tree to extract docstring from.
            sections: Code sections to update with module docstring.
        """
        if (
            tree.body
            and isinstance(tree.body[0], ast.Expr)
            and isinstance(tree.body[0].value, ast.Constant)
            and isinstance(tree.body[0].value.value, str)
            and sections["module_docstring"] is None
        ):
            sections["module_docstring"] = ast.get_docstring(tree, clean=True)

    def _append_if_source(self, block: CodeBlock, node: ast.AST, dest: list[str]) -> None:
        segment = ast.get_source_segment(block.content, node)
        if segment:
            dest.append(segment)

    def _handle_assignment_node(
        self, node: ast.AST, block: CodeBlock, tree: ast.Module, sections: CodeSections
    ) -> None:
        # Narrow type locally to satisfy static type checkers; runtime behavior unchanged
        if isinstance(node, ast.Assign | ast.AnnAssign):
            var_code = ast.get_source_segment(block.content, node)
            if var_code and self._is_top_level_assignment(node, tree):
                sections["globals"].append(var_code)

    def _bucket_node(
        self, node: ast.AST, block: CodeBlock, tree: ast.Module, sections: CodeSections
    ) -> None:
        """
        Categorize an AST node into the appropriate section bucket.

        Args:
            node: AST node to categorize.
            block: Source code block containing the node.
            tree: Complete AST module tree for context.
            sections: Code sections to update with categorized code.
        """
        if isinstance(node, ast.FunctionDef):
            self._append_if_source(block, node, sections["functions"])
        elif isinstance(node, ast.ClassDef):
            self._append_if_source(block, node, sections["classes"])
        elif isinstance(node, ast.Assign | ast.AnnAssign):
            self._handle_assignment_node(node, block, tree, sections)
        elif not isinstance(node, ast.Import | ast.ImportFrom):
            self._append_if_source(block, node, sections["main"])

    def _record_block_syntax_failure(self, block: CodeBlock, sections: CodeSections) -> None:
        """
        Record and handle syntax errors in code blocks by adding to main section.

        Args:
            block: Code block that failed to parse.
            sections: Code sections to update with unparseable code.
        """
        logger.warning("Could not parse block: %s", block.line_numbers)
        context = ErrorContext(
            line_number=block.line_numbers[0],
            code_snippet=block.content[:100],
            metadata={"fallback": "treating as main code"},
        )
        error = AssemblyError(
            "Could not parse code block structure",
            assembly_stage="sections",
            context=context,
        )
        error.add_suggestion("Check syntax in this block")
        error.add_suggestion("Ensure proper Python formatting")
        logger.warning(error.format_error())
        sections["main"].append(block.content)

    def _organize_code_sections(self, blocks: list[CodeBlock]) -> CodeSections:
        """
        Organize code into sections (functions, classes, globals, main).

        Args:
            blocks: List of Python code blocks to organize into logical sections.

        Returns:
            Dictionary with categorized code sections, properly typed as CodeSections.
        """
        sections = self._init_section_buckets()

        for block in blocks:
            try:
                tree = parse_cached(block.content)
                # Check for module docstring with identical semantics
                if isinstance(tree, ast.Module):
                    self._maybe_set_module_docstring(tree, sections)
                    # Bucket each top-level node exactly as before
                    for node in tree.body:
                        self._bucket_node(node, block, tree, sections)
            except SyntaxError:
                self._record_block_syntax_failure(block, sections)

        return sections

    def _first_named_node(self, tree: ast.AST, expected_type: type) -> str | None:
        """Return the first top-level node name if it matches expected_type, else None."""
        if not isinstance(tree, ast.Module) or not getattr(tree, "body", None):
            return None
        first = tree.body[0]
        if isinstance(first, expected_type):
            return getattr(first, "name", None)
        return None

    def _first_function_name(self, tree: ast.AST) -> str | None:
        """Return the first top-level function name from an ast.Module, else None."""
        return self._first_named_node(tree, ast.FunctionDef)

    def _first_class_name(self, tree: ast.AST) -> str | None:
        """Return the first top-level class name from an ast.Module, else None."""
        return self._first_named_node(tree, ast.ClassDef)

    def _merge_functions(self, functions: list[str]) -> str:
        """
        Merge function definitions, handling duplicates by keeping later definitions.

        Args:
            functions: List of function code strings to merge and deduplicate.

        Returns:
            Merged functions section as a single string with proper spacing.
            Returns empty string if no functions provided.
        """
        if not functions:
            return ""

        # Use OrderedDict to maintain order and handle duplicates
        unique_functions: OrderedDict[str, str] = OrderedDict()

        for func_code in functions:
            try:
                # Parse function to get its name
                tree = parse_cached(func_code)
                if func_name := self._first_function_name(tree):
                    # If duplicate, keep the later definition
                    # (assumed to be more complete)
                    unique_functions[func_name] = func_code
                else:
                    # If we can't parse a name, use the code as-is with a unique key
                    unique_key = f"func_{len(unique_functions)}"
                    unique_functions[unique_key] = func_code

            except SyntaxError as e:
                # If parsing fails, include anyway
                logger.warning("Could not parse function: %s", str(e))
                unique_functions[f"func_{len(unique_functions)}"] = func_code

        return "\n\n".join(unique_functions.values())

    def _merge_classes(self, classes: list[str]) -> str:
        """
        Merge class definitions, handling duplicates by keeping later definitions.

        Args:
            classes: List of class code strings to merge and deduplicate.

        Returns:
            Merged classes section as a single string with proper spacing.
            Returns empty string if no classes provided.
        """
        if not classes:
            return ""

        unique_classes: OrderedDict[str, str] = OrderedDict()

        for class_code in classes:
            try:
                tree = parse_cached(class_code)
                if class_name := self._first_class_name(tree):
                    unique_classes[class_name] = class_code
                else:
                    unique_classes[f"class_{len(unique_classes)}"] = class_code
            except SyntaxError as e:
                logger.warning("Could not parse class: %s", str(e))
                unique_classes[f"class_{len(unique_classes)}"] = class_code

        return "\n\n".join(unique_classes.values())

    def _is_constant_assignment_line(self, global_code: str) -> bool:
        """Return True if the assignment line matches the constant heuristic."""
        return re.search(CONSTANT_ASSIGNMENT_PATTERN, global_code.strip()) is not None

    def _split_globals(self, globals_list: list[str]) -> tuple[list[str], list[str]]:
        """Return (constants, variables) preserving original per-item order and trimming behavior."""
        constants: list[str] = []
        variables: list[str] = []
        for global_code in globals_list:
            stripped = global_code.strip()
            if self._is_constant_assignment_line(global_code):
                constants.append(stripped)
            else:
                variables.append(stripped)
        return constants, variables

    def _build_globals_section_lines(self, constants: list[str], variables: list[str]) -> list[str]:
        """Construct globals section lines with exact headers and blank-line rules."""
        lines: list[str] = []
        if constants:
            lines.append(GLOBALS_CONSTANTS_HEADER)
            lines.extend(constants)
        if variables:
            if constants:
                lines.append("")
            lines.append(GLOBALS_VARIABLES_HEADER)
            lines.extend(variables)
        return lines

    def _organize_globals(self, globals_list: list[str]) -> str:
        """
        Organize global variables and constants with proper categorization.

        Args:
            globals_list: List of global assignment strings to organize.

        Returns:
            Organized globals section with constants first, then variables.
            Includes section headers and proper spacing.
            Returns empty string if no globals provided.
        """
        if not globals_list:
            return ""

        # Classify globals into constants vs variables
        constants, variables = self._split_globals(globals_list)

        # Build output lines for the globals section
        lines = self._build_globals_section_lines(constants, variables)
        return "\n".join(lines)

    def _organize_main_code(self, main_sections: list[str]) -> str:
        """
        Organize main execution code with appropriate guard if needed.

        Args:
            main_sections: List of main code sections to organize.

        Returns:
            Organized main code section, potentially wrapped in if __name__ == "__main__": guard.
            Returns empty string if no main code provided.
        """
        if not main_sections:
            return ""

        # Check if we should wrap in if __name__ == "__main__":
        needs_main_guard = any(
            "print(" in code or "input(" in code or re.search(
                r"\b(main|run|execute)\s*\(", code)
            for code in main_sections
        )

        main_code = "\n\n".join(main_sections)

        if needs_main_guard:
            # Indent the main code
            indented_code = "\n".join(
                f"{' ' * self.indent_size}{line}" if line.strip() else line
                for line in main_code.splitlines()
            )
            return f'if __name__ == "__main__":\n{indented_code}'

        return main_code

    def _ensure_consistency(self, code: str) -> str:
        """
        Ensure consistency in the assembled code by fixing indentation and formatting.

        Args:
            code: Assembled code requiring consistency checks and formatting fixes.

        Returns:
            Code with consistent indentation, line endings, and spacing.
        """
        # Fix indentation
        code = self._fix_indentation(code)

        # Ensure consistent line endings
        code = code.replace("\r\n", "\n").replace("\r", "\n")

        # Remove excessive blank lines
        code = re.sub(r"\n{4,}", "\n\n\n", code)

        # Ensure newline at end of file
        if code and not code.endswith("\n"):
            code += "\n"

        return code

    def _detect_indent_char(self, lines: list[str]) -> str:
        """Return "\t" if any line starts with a tab, else " "."""
        for line in lines:
            if line.startswith("\t"):
                return "\t"
        return " "

    def _convert_tabs_to_spaces_if_needed(self, lines: list[str], indent_char: str) -> list[str]:
        """If indent_char is "\t" and indent_size is set, replace tabs with spaces."""
        if indent_char == "\t" and self.indent_size:
            return [line.replace("\t", " " * self.indent_size) for line in lines]
        return lines

    def _should_dedent_keyword(self, stripped: str) -> bool:
        """Return True if stripped starts with any dedent keyword."""
        return stripped.startswith(DEDENT_KEYWORDS)

    def _dedent_to_match_stack(self, indent_stack: list[int], current_indent: int) -> int:
        """While current_indent &lt; top of stack and stack depth &gt; 1, pop; return new top."""
        while len(indent_stack) > 1 and current_indent < indent_stack[-1]:
            indent_stack.pop()
        return indent_stack[-1]

    def _handle_block_start(
        self, stripped: str, current_indent: int, indent_stack: list[int]
    ) -> None:
        """Push next indent level when a block starts."""
        if stripped.endswith(":") and not stripped.startswith("#"):
            indent_stack.append(current_indent + self.indent_size)

    def _fix_indentation(self, code: str) -> str:
        """
        Fix and standardize indentation in the code.

        Args:
            code: Code with potential indentation issues to be fixed.

        Returns:
            Code with fixed and standardized indentation using configured indent size.

        Raises:
            AssemblyError: If indentation fixing fails due to severe syntax issues.
        """
        try:
            lines = code.splitlines()
            fixed_lines: list[str] = []

            # Detect current indentation style
            indent_char = self._detect_indent_char(lines)

            # Convert all indentation to spaces if configured
            lines = self._convert_tabs_to_spaces_if_needed(lines, indent_char)

            # Fix indentation levels
            indent_stack = [0]

            for line in lines:
                stripped = line.strip()

                if not stripped:
                    fixed_lines.append("")
                    continue

                # Calculate current indentation
                current_indent = len(line) - len(line.lstrip())

                # Check for dedent keywords
                if self._should_dedent_keyword(stripped) and len(indent_stack) > 1:
                    # These should be at the same level as their matching statement
                    indent_stack.pop()
                    current_indent = indent_stack[-1]

                # Check for block start
                if stripped.endswith(":") and not stripped.startswith("#"):
                    fixed_lines.append(" " * current_indent + stripped)
                    self._handle_block_start(
                        stripped, current_indent, indent_stack)
                else:
                    # Adjust indentation based on context
                    if current_indent < indent_stack[-1] and len(indent_stack) > 1:
                        # Dedent detected
                        current_indent = self._dedent_to_match_stack(
                            indent_stack, current_indent)

                    fixed_lines.append(" " * current_indent + stripped)

            return "\n".join(fixed_lines)
        except Exception as e:
            error = AssemblyError(
                "Failed to fix indentation", assembly_stage="indentation", cause=e
            )
            error.add_suggestion("Check for severe indentation errors")
            error.add_suggestion("Ensure consistent use of spaces or tabs")
            raise error from e

    def _categorize_import(self, module_name: str) -> str:
        """
        Categorize an import as standard, third-party, or local.

        Args:
            module_name: Name of the module to categorize.

        Returns:
            Category string: 'standard', 'third_party', or 'local'.
        """
        # Standard library modules (Python 3.8+)
        standard_lib = {
            "abc",
            "aifc",
            "argparse",
            "array",
            "ast",
            "asynchat",
            "asyncio",
            "asyncore",
            "atexit",
            "audioop",
            "base64",
            "bdb",
            "binascii",
            "binhex",
            "bisect",
            "builtins",
            "bz2",
            "calendar",
            "cgi",
            "cgitb",
            "chunk",
            "cmath",
            "cmd",
            "code",
            "codecs",
            "codeop",
            "collections",
            "colorsys",
            "compileall",
            "concurrent",
            "configparser",
            "contextlib",
            "contextvars",
            "copy",
            "copyreg",
            "cProfile",
            "crypt",
            "csv",
            "ctypes",
            "curses",
            "dataclasses",
            "datetime",
            "dbm",
            "decimal",
            "difflib",
            "dis",
            "distutils",
            "doctest",
            "email",
            "encodings",
            "ensurepip",
            "enum",
            "errno",
            "faulthandler",
            "fcntl",
            "filecmp",
            "fileinput",
            "fnmatch",
            "formatter",
            "fractions",
            "ftplib",
            "functools",
            "gc",
            "getopt",
            "getpass",
            "gettext",
            "glob",
            "grp",
            "gzip",
            "hashlib",
            "heapq",
            "hmac",
            "html",
            "http",
            "imaplib",
            "imghdr",
            "imp",
            "importlib",
            "inspect",
            "io",
            "ipaddress",
            "itertools",
            "json",
            "keyword",
            "lib2to3",
            "linecache",
            "locale",
            "logging",
            "lzma",
            "mailbox",
            "mailcap",
            "marshal",
            "math",
            "mimetypes",
            "mmap",
            "modulefinder",
            "msilib",
            "msvcrt",
            "multiprocessing",
            "netrc",
            "nis",
            "nntplib",
            "numbers",
            "operator",
            "optparse",
            "os",
            "ossaudiodev",
            "parser",
            "pathlib",
            "pdb",
            "pickle",
            "pickletools",
            "pipes",
            "pkgutil",
            "platform",
            "plistlib",
            "poplib",
            "posix",
            "posixpath",
            "pprint",
            "profile",
            "pstats",
            "pty",
            "pwd",
            "py_compile",
            "pyclbr",
            "pydoc",
            "queue",
            "quopri",
            "random",
            "re",
            "readline",
            "reprlib",
            "resource",
            "rlcompleter",
            "runpy",
            "sched",
            "secrets",
            "select",
            "selectors",
            "shelve",
            "shlex",
            "shutil",
            "signal",
            "site",
            "smtpd",
            "smtplib",
            "sndhdr",
            "socket",
            "socketserver",
            "spwd",
            "sqlite3",
            "ssl",
            "stat",
            "statistics",
            "string",
            "stringprep",
            "struct",
            "subprocess",
            "sunau",
            "symbol",
            "symtable",
            "sys",
            "sysconfig",
            "syslog",
            "tabnanny",
            "tarfile",
            "telnetlib",
            "tempfile",
            "termios",
            "test",
            "textwrap",
            "threading",
            "time",
            "timeit",
            "tkinter",
            "token",
            "tokenize",
            "trace",
            "traceback",
            "tracemalloc",
            "tty",
            "turtle",
            "turtledemo",
            "types",
            "typing",
            "unicodedata",
            "unittest",
            "urllib",
            "uu",
            "uuid",
            "venv",
            "warnings",
            "wave",
            "weakref",
            "webbrowser",
            "winreg",
            "winsound",
            "wsgiref",
            "xdrlib",
            "xml",
            "xmlrpc",
            "zipapp",
            "zipfile",
            "zipimport",
            "zlib",
            "zoneinfo",
        }

        # Get top-level module name
        top_level = module_name.split(".")[0]

        if top_level in standard_lib:
            return "standard"
        if module_name.startswith(".") or not module_name:
            return "local"
        return "third_party"

    def _is_top_level_assignment(self, node: ast.stmt, tree: ast.Module) -> bool:
        """
        Check if an assignment is at the top level (not inside a function/class).

        Args:
            node: AST statement node to check for top-level status.
            tree: Full AST module tree for context analysis.

        Returns:
            True if the assignment is at module top-level, False otherwise.
        """
        # Check if the node is directly in the module body
        if hasattr(tree, "body") and node in tree.body:
            return True

        # Walk the tree to find the node's parent
        for parent_node in ast.walk(tree):
            # Check if node is inside a function or class
            if isinstance(parent_node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
                # Check if our node is within this function/class
                for child in ast.walk(parent_node):
                    if child is node:
                        return False

        # If we get here, it's likely top-level
        return True

    def _usage_pattern(self, name: str) -> str:
        """
        Build the exact regex string used to detect a callsite for a common name.
        Equivalent to the inline construction rf"\\b{name}\\s*\\(" with identical semantics.
        """
        return rf"\b{name}\s*\("

    def _already_imported_standard(
        self,
        module: str,
        name: str,
        imports: dict[str, set[str]],
        from_imports: dict[str, dict[str, set[str]]],
    ) -> bool:
        """
        Return True if the 'standard' category already contains either:
        - A plain import of the module in imports["standard"], OR
        - A from-import entry for this module that already includes the name in from_imports["standard"][module].
        This performs presence checks without mutating the provided dictionaries.
        """
        standard_imports = imports.get("standard", set())
        standard_from_imports = from_imports.get("standard", {})
        return (module in standard_imports) or (name in standard_from_imports.get(module, set()))

    def _add_standard_from_import(
        self,
        module: str,
        name: str,
        from_imports: dict[str, dict[str, set[str]]],
    ) -> None:
        """
        Ensure from_imports["standard"][module] exists and add the name to its set.
        Emits the same debug message as the original implementation.
        """
        if module not in from_imports["standard"]:
            from_imports["standard"][module] = set()
        from_imports["standard"][module].add(name)
        logger.debug("Auto-adding import: from %s import %s", module, name)

    def _add_common_imports(
        self,
        blocks: list[CodeBlock],
        imports: dict[str, set[str]],
        from_imports: dict[str, dict[str, set[str]]],
    ) -> None:
        """
        Auto-add common imports based on code usage patterns.

        Args:
            blocks: List of code blocks to analyze for common patterns.
            imports: Current imports dictionary to update with common imports.
            from_imports: Current from-imports dictionary to update.
        """
        # Combine all code for analysis
        all_code = "\n".join(block.content for block in blocks)

        for module, common_names in self.common_imports.items():
            for name in common_names:
                # Check if the name is used in the code
                pattern = self._usage_pattern(name)
                if re.search(pattern, all_code):
                    # Check if already imported
                    if self._already_imported_standard(module, name, imports, from_imports):
                        continue

                    # Add the import
                    self._add_standard_from_import(module, name, from_imports)

    def _organize_comments(self, comment_blocks: list[CodeBlock]) -> str:
        """
        Organize comment blocks into a cohesive comments section.

        Args:
            comment_blocks: List of comment blocks to organize.

        Returns:
            Organized comments section as a string.
        """
        comments: list[str] = []

        for block in comment_blocks:
            content = block.content.strip()
            if content:
                comments.append(content)

        return "\n".join(comments)

    def _rstrip_lines(self, code: str) -> list[str]:
        """Return code.splitlines() with rstrip applied to each line."""
        return [line.rstrip() for line in code.splitlines()]

    def _is_top_level_definition_line(self, line: str, i: int, lines: list[str]) -> bool:
        """Return True if line matches the definition-line heuristic used in _final_cleanup()."""
        return (
            line.startswith(("def ", "class "))
            or i > 0
            and not lines[i - 1].strip()
            and bool(line.strip())
            and not line[0].isspace()
        )

    def _apply_pre_definition_spacing(self, cleaned_lines: list[str], i: int) -> None:
        """Mutate cleaned_lines to ensure exactly two blank lines immediately before a definition."""
        while len(cleaned_lines) >= 2 and not cleaned_lines[-1] and not cleaned_lines[-2]:
            cleaned_lines.pop()
        if cleaned_lines and cleaned_lines[-1]:
            cleaned_lines.append("")
        if len(cleaned_lines) < 2 or cleaned_lines[-2]:
            cleaned_lines.append("")

    def _ensure_eof_newline(self, text: str) -> str:
        """Ensure a single trailing newline at EOF if text is non-empty."""
        if text and not text.endswith("\n"):
            text += "\n"
        return text

    def _final_cleanup(self, code: str) -> str:
        """
        Perform final cleanup on the assembled code with proper formatting.

        Args:
            code: Assembled code requiring final cleanup and formatting.

        Returns:
            Cleaned up code with proper whitespace, spacing, and formatting.
        """
        # Remove trailing whitespace from lines
        trimmed_lines = self._rstrip_lines(code)

        # Ensure proper spacing around top-level definitions
        cleaned_lines: list[str] = []
        prev_was_definition: bool = False

        for i, line in enumerate(trimmed_lines):
            # Check if this is a top-level definition
            is_definition: bool = self._is_top_level_definition_line(
                line, i, trimmed_lines)

            # Add spacing before definitions (except the first)
            if is_definition and prev_was_definition and cleaned_lines:
                # Ensure two blank lines before definition
                self._apply_pre_definition_spacing(cleaned_lines, i)

            cleaned_lines.append(line)
            prev_was_definition = is_definition and bool(line.strip())

        # Join and ensure single newline at end
        final_code = "\n".join(cleaned_lines)
        return self._ensure_eof_newline(final_code)

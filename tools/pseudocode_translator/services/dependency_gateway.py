from __future__ import annotations

from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    import logging


# Keep this module free of translator.py imports to avoid cycles.


class DependencyAnalysisGateway:
    """
    Gateway that encapsulates dependency analysis for processed CodeBlock lists.

    Behavior preservation requirements:
    - Attempts to use translator_support.dependency_resolver.DependencyResolver if importable.
      Semantics must match translator._handle_dependencies() resolver path:
        * For each PYTHON block, merge cumulative defined_names and required_imports.
        * On missing analysis info, record empty lists for that block.
        * Never raise from dependency handling.
    - If resolver import or analyze fails, falls back to in-process parsing using parse_cached(AST),
      mirroring translator's non-resolver path:
        * Accumulate names/imports across blocks in order.
        * On SyntaxError for a given block: log warning
          "Could not parse block {i} for dependency analysis" and set empty lists.
    - Metadata keys remain identical: "defined_names", "required_imports".
    """

    def __init__(self, parse_cached: Any, logger: logging.Logger) -> None:
        self._parse_cached = parse_cached
        self._logger = logger

    def analyze_and_annotate(self, blocks: list[Any]) -> None:
        """Annotate blocks in-place with dependency metadata; never raises."""
        defined_names: set[str] = set()
        required_imports: set[str] = set()

        resolver = self._get_resolver()
        if resolver is not None:
            analyses = self._safe_analyze_blocks(resolver, blocks)
            self._annotate_resolver_blocks(blocks, analyses, defined_names, required_imports)
            return

    def _get_resolver(self) -> Any:
        try:
            from ..translator_support.dependency_resolver import DependencyResolver  # type: ignore

            return DependencyResolver(use_cache=True)
        except ImportError:
            return None

    def _safe_analyze_blocks(self, resolver: Any, blocks: list[Any]) -> list[dict[str, list[str]]]:
        try:
            return resolver.analyze_blocks(blocks)
        except (AttributeError, ValueError, TypeError):
            return []

    def _annotate_resolver_blocks(
        self,
        blocks: list[Any],
        analyses: list[dict[str, list[str]]],
        defined_names: set[str],
        required_imports: set[str],
    ) -> None:
        for i, block in enumerate(blocks):
            try:
                block_type = getattr(block, "type", None)
                if str(getattr(block_type, "value", block_type)).lower() != "python":
                    continue

                result = (
                    analyses[i]
                    if i < len(analyses)
                    else {"defined_names": [], "required_imports": []}
                )
                dn = result.get("defined_names", []) or []
                ri = result.get("required_imports", []) or []

                if dn or ri:
                    defined_names.update(dn)
                    required_imports.update(ri)
                    block.metadata["defined_names"] = list(defined_names)
                    block.metadata["required_imports"] = list(required_imports)
                else:
                    block.metadata["defined_names"] = []
                    block.metadata["required_imports"] = []
            except (AttributeError, ValueError, TypeError, KeyError):
                try:
                    block.metadata["defined_names"] = []
                    block.metadata["required_imports"] = []
                except (AttributeError, TypeError):
                    pass

        # Fallback: in-process AST walk with parse_cached
        import ast

        for i, block in enumerate(blocks):
            try:
                block_type = getattr(block, "type", None)
                if str(getattr(block_type, "value", block_type)).lower() != "python":
                    continue

                try:
                    tree = self._parse_cached(block.content)
                except SyntaxError:
                    self._logger.warning(f"Could not parse block {i} for dependency analysis")
                    block.metadata["defined_names"] = []
                    block.metadata["required_imports"] = []
                    continue

                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef | ast.ClassDef):
                        defined_names.add(node.name)
                    elif isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Name):
                                defined_names.add(target.id)
                    elif isinstance(node, ast.Import):
                        for alias in node.names:
                            required_imports.add(f"import {alias.name}")
                    elif isinstance(node, ast.ImportFrom):
                        module = node.module or ""
                        for alias in node.names:
                            required_imports.add(f"from {module} import {alias.name}")

                block.metadata["defined_names"] = list(defined_names)
                block.metadata["required_imports"] = list(required_imports)

            except (ValueError, TypeError, AttributeError, SyntaxError):
                # Never raise; ensure metadata keys exist
                try:
                    block.metadata["defined_names"] = []
                    block.metadata["required_imports"] = []
                except (AttributeError, TypeError):
                    pass

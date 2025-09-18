"""
Models package for the Pseudocode Translator

This module defines the core dataclasses and enums used by the parser and validator.
It intentionally avoids dynamic import hacks to keep static typing reliable.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class BlockType(Enum):
    ENGLISH = "english"
    PYTHON = "python"
    MIXED = "mixed"
    COMMENT = "comment"


@dataclass
class CodeBlock:
    type: BlockType
    content: str
    line_numbers: tuple[int, int]
    metadata: dict[str, Any]
    context: str | None = None


@dataclass
class ParseError:
    message: str
    line_number: int | None = None
    block_content: str | None = None
    suggestion: str | None = None


@dataclass
class ParseResult:
    blocks: list[CodeBlock]
    errors: list[ParseError]
    warnings: list[str]


__all__ = ["BlockType", "CodeBlock", "ParseError", "ParseResult"]

# Optional future imports (do not fail module import if missing)
try:
    from .base import BaseModel, ModelCapabilities, ModelFormat  # noqa: F401

    __all__.extend(["BaseModel", "ModelCapabilities", "ModelFormat"])
except Exception:
    pass

try:
    from .registry import ModelRegistry, register_model  # noqa: F401

    __all__.extend(["ModelRegistry", "register_model"])
except Exception:
    pass

try:
    from .manager import ModelManager  # noqa: F401

    __all__.append("ModelManager")
except Exception:
    pass

try:
    from .downloader import ModelDownloader  # noqa: F401

    __all__.append("ModelDownloader")
except Exception:
    pass


# Optional auto-discovery helper
def auto_discover_models() -> None:
    """Auto-discover and import model implementation modules under this package."""
    import importlib
    import logging
    from pathlib import Path
    import pkgutil

    package_dir = Path(__file__).parent
    for _, module_name, _ in pkgutil.iter_modules([str(package_dir)]):
        if module_name not in {"base", "registry", "manager", "downloader", "__init__"}:
            try:
                importlib.import_module(f".{module_name}", package=__name__)
            except Exception as e:
                logging.debug(f"Model module '{module_name}' not ready: {e}")

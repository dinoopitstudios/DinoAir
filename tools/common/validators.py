"""Common input validators and a lightweight validation decorator.

These helpers provide consistent, unit-friendly validation utilities with strict typing
and predictable error messages that callers can map to outward-facing strings.
"""

from __future__ import annotations

import inspect
from functools import wraps
from pathlib import Path
from typing import TYPE_CHECKING, Any, ParamSpec, TypeVar

if TYPE_CHECKING:
    from collections.abc import Callable


P = ParamSpec("P")
R = TypeVar("R")


def validate_non_empty_str(name: str, value: str) -> None:
    """Validate that a string is present and not just whitespace.

    Raises:
        ValueError: If empty/whitespace.
    """
    if value is None or not str(value).strip():
        raise ValueError(f"{name} is required")


def _normalize_to_path(value: Any) -> Path:
    """Convert input to Path, mirroring current behavior of Path(value).

    Note:
        Accepts types supported by pathlib.Path (e.g., str, os.PathLike).
        For None or unsupported types, this explicitly re-raises the same TypeError
        that pathlib.Path would raise, preserving current behavior and messages.
    """
    try:
        return Path(value)
    except TypeError as te:
        # Explicitly re-raise to make intent clear without changing the message
        raise te


def _classify_path_error(exc: Exception) -> str:
    """
    Classify a path-related error message into a stable category.

    Returns:
        str: One of "not_found", "not_file", "not_dir", or "other".

    Classification is based on exact messages currently raised by validate_path_exists():
      - "Path does not exist:"   -> "not_found"
      - "Path is not a file:"    -> "not_file"
      - "Path is not a directory:" -> "not_dir"
      - otherwise                -> "other"
    """
    msg = str(exc)
    if msg.startswith("Path does not exist:"):
        return "not_found"
    if msg.startswith("Path is not a file:"):
        return "not_file"
    return "not_dir" if msg.startswith("Path is not a directory:") else "other"


def _check_exists(p: Path, raw_value: Any) -> None:
    """Raise ValueError with existing canonical message when path does not exist."""
    if not p.exists():
        raise ValueError(f"Path does not exist: {raw_value}")


def _check_file(p: Path, raw_value: Any) -> None:
    """Raise ValueError with existing canonical message when path is not a file."""
    if not p.is_file():
        raise ValueError(f"Path is not a file: {raw_value}")


def _check_dir(p: Path, raw_value: Any) -> None:
    """Raise ValueError with existing canonical message when path is not a directory."""
    if not p.is_dir():
        raise ValueError(f"Path is not a directory: {raw_value}")


def _validate_type_flags(_must_be_file: bool | None, _must_be_dir: bool | None) -> None:
    """Preserve current behavior: allow any combination; no pre-validation."""
    return


def validate_path_exists(
    path: str, must_be_file: bool | None = None, must_be_dir: bool | None = None
) -> Path:
    """Validate that a path exists and optionally its type.

    Returns:
        Path: The original path as a Path object (unmodified).

    Raises:
        ValueError: With canonical messages:
          - "Path does not exist: {path}"
          - "Path is not a file: {path}"       (when must_be_file is True)
          - "Path is not a directory: {path}"  (when must_be_dir is True)
    """
    _validate_type_flags(must_be_file, must_be_dir)
    p = _normalize_to_path(path)

    _check_exists(p, path)

    if must_be_file:
        _check_file(p, path)

    if must_be_dir:
        _check_dir(p, path)

    return p


def validate_list_non_empty(name: str, items: list[Any]) -> None:
    """Validate that a list is provided and not empty.

    Raises:
        ValueError: If the list is empty or None.
    """
    if not items:
        raise ValueError(f"{name} list is required and cannot be empty")


def validate_args(
    mapping: dict[str, tuple[Callable[..., None], ...]],
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator to validate named args before the wrapped function executes.

    mapping: Dict where keys are argument names and values are tuples of validators.
             Each validator is called in order for the argument's value.
             A validator may accept either:
               - (name: str, value: Any), or
               - (value: Any)
             The first failure should raise ValueError and prevent execution.

    The original function's signature and docstring are preserved via wraps.
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        sig = inspect.signature(func)

        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            bound = sig.bind_partial(*args, **kwargs)
            arguments = bound.arguments

            for arg_name, validators in mapping.items():
                if arg_name not in arguments:
                    # Argument not provided; skip validation for this arg.
                    continue
                value = arguments[arg_name]

                for validator in validators:
                    # Try (name, value) first; fall back to (value,)
                    try:
                        validator(arg_name, value)  # type: ignore[misc]
                    except TypeError:
                        validator(value)  # type: ignore[misc]

            return func(*args, **kwargs)

        return wrapper

    return decorator

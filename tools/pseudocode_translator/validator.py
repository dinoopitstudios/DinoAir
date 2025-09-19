"""
Validator module for the Pseudocode Translator

This module handles validation of generated Python code, including
syntax validation, logic checks, and improvement suggestions.

NOTE: This module has been refactored to improve code health by separating
concerns into focused modules. All classes are re-exported here to maintain
full backward compatibility.
"""

# Import all classes from the refactored validator package to maintain backward compatibility
from .validator import (
    PerformanceChecker,
    RuntimeRiskChecker,
    Scope,
    TypeConsistencyChecker,
    UndefinedVariableChecker,
    ValidationErrorParams,
    ValidationResult,
    Validator,
)

# Re-export all classes for backward compatibility
__all__ = [
    "Validator",
    "ValidationResult",
    "ValidationErrorParams",
    "Scope",
    "TypeConsistencyChecker",
    "RuntimeRiskChecker",
    "PerformanceChecker",
    "UndefinedVariableChecker",
]

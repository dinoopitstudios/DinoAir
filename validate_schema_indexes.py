#!/usr/bin/env python3
"""
Schema validation script to verify comprehensive index coverage in SCHEMA_DDLS
"""

import re
import sys
import traceback
from pathlib import Path

from database.initialize_db import SCHEMA_DDLS

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))


def extract_indexes_from_schema(schema_lines: list[str]) -> list[tuple[str, str]]:
    """Extract index definitions from schema DDL"""
    indexes = []

    for ddl in schema_lines:
        ddl = ddl.strip()
        if ddl.startswith(("CREATE INDEX", "CREATE UNIQUE INDEX")):
            # Extract index name
            match = re.search(r"CREATE (?:UNIQUE )?INDEX (?:IF NOT EXISTS )?(\w+)", ddl)
            if match:
                index_name = match.group(1)
                indexes.append((index_name, ddl))

    return indexes


def validate_notes_indexes() -> bool:
    """Validate that our notes schema has comprehensive index coverage"""

    # Expected indexes based on our analysis
    expected_patterns = [
        "is_deleted",  # Single column for filtering deleted notes
        "updated_at",  # Single column for date sorting
        "created_at",  # Single column for creation date
        "project_id",  # Single column for project filtering
        "is_deleted.*updated_at",  # Compound for active notes by date
        "is_deleted.*project_id.*updated_at",  # Compound for project notes by date
        "is_deleted.*title",  # Compound for title searches on active notes
        "is_deleted.*project_id.*title",  # Compound for project title searches
        "project_id.*updated_at",  # Compound for project sorting
        "title.*updated_at",  # Compound for title-based sorting
        "tags.*NOT NULL",  # Partial index for tagged notes
        "project_id.*IS NULL",  # Partial index for notes without project
    ]

    notes_schema = SCHEMA_DDLS.get("notes", [])
    indexes = extract_indexes_from_schema(notes_schema)

    # Show all indexes
    for _idx_name, ddl in indexes:
        # Show simplified DDL
        simplified = re.sub(r"\s+", " ", ddl).strip()
        if len(simplified) > 80:
            simplified = simplified[:77] + "..."

    # Check coverage of expected patterns

    index_ddls = " ".join([ddl for _, ddl in indexes]).lower()

    covered_patterns = []
    missing_patterns = []

    for pattern in expected_patterns:
        pattern_lower = pattern.lower()
        if re.search(pattern_lower.replace(".*", r".*?"), index_ddls):
            covered_patterns.append(pattern)
        else:
            missing_patterns.append(pattern)

    if missing_patterns:
        pass

    # Analyze specific query scenarios

    scenarios = [
        ("Get active notes by date", ["is_deleted", "updated_at"]),
        ("Get project notes by date", ["is_deleted", "project_id", "updated_at"]),
        ("Search active note titles", ["is_deleted", "title"]),
        ("Search project note titles", ["is_deleted", "project_id", "title"]),
        ("Get notes with tags", ["tags"]),
        ("Get notes without project", ["project_id"]),
    ]

    for _scenario, required_columns in scenarios:
        # Check if we have an index covering these columns
        found_match = False
        for _idx_name, ddl in indexes:
            ddl_lower = ddl.lower()
            if all(col.lower() in ddl_lower for col in required_columns):
                found_match = True
                break

    success = len(missing_patterns) == 0

    if success:
        pass
    else:
        pass

    return success


def main() -> bool:
    """Main validation function"""
    try:
        return validate_notes_indexes()
    except Exception:
        traceback.print_exc()
        return False


if __name__ == "__main__":
    sys.exit(0 if main() else 1)

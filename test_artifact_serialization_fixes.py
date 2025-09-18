#!/usr/bin/env python3
"""
Test script to verify the fixes for artifact.py data serialization.

This script verifies that:
1. asdict() output is not mutated in-place
2. List fields (tags, encrypted_fields) are JSON-encoded instead of comma-joined
3. from_dict properly JSON-decodes list fields back to Python lists
4. Dict fields (metadata, properties) continue to use JSON encoding/decoding
5. Edge cases with None values and invalid JSON are handled safely
"""

import json
import sys
from pathlib import Path

from models.artifact import Artifact

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))


def test_no_in_place_mutation():
    """Test that asdict() output is not mutated in-place."""

    artifact = Artifact(
        id="test1", tags=["python", "test"], encrypted_fields=["content", "metadata"]
    )

    # Get the original asdict output
    from dataclasses import asdict

    original_dict = asdict(artifact)
    original_tags = original_dict["tags"].copy()
    original_encrypted_fields = original_dict["encrypted_fields"].copy()

    # Call to_dict (which previously mutated the asdict output)
    artifact.to_dict()

    # Verify the original asdict output was not mutated
    if original_dict["tags"] != original_tags:
        raise AssertionError(f"tags were mutated: {original_dict['tags']} != {original_tags}")
    if original_dict["encrypted_fields"] != original_encrypted_fields:
        raise AssertionError(
            f"encrypted_fields were mutated: {original_dict['encrypted_fields']} != {original_encrypted_fields}"
        )


def test_json_encoding_for_lists():
    """Test that list fields are JSON-encoded instead of comma-joined."""

    artifact = Artifact(
        id="test2",
        tags=["python", "test", "example"],
        encrypted_fields=["content", "metadata", "description"],
    )

    artifact_dict = artifact.to_dict()

    # Verify that list fields are JSON-encoded strings
    assert isinstance(artifact_dict["tags"], str), (
        f"tags should be string, got {type(artifact_dict['tags'])}"
    )
    assert isinstance(artifact_dict["encrypted_fields"], str), (
        f"encrypted_fields should be string, got {type(artifact_dict['encrypted_fields'])}"
    )

    # Verify that the strings are valid JSON and decode to the original lists
    decoded_tags = json.loads(artifact_dict["tags"])
    decoded_encrypted_fields = json.loads(artifact_dict["encrypted_fields"])

    if decoded_tags != [
        "python",
        "test",
        "example",
    ]:
        raise AssertionError(f"decoded tags don't match: {decoded_tags}")
    if decoded_encrypted_fields != [
        "content",
        "metadata",
        "description",
    ]:
        raise AssertionError(f"decoded encrypted_fields don't match: {decoded_encrypted_fields}")

    # Verify it's NOT comma-joined (would fail if it was)
    if artifact_dict["tags"] == "python,test,example":
        raise AssertionError("tags should not be comma-joined")
    if artifact_dict["encrypted_fields"] == "content,metadata,description":
        raise AssertionError("encrypted_fields should not be comma-joined")


def test_json_decoding_roundtrip():
    """Test that from_dict properly JSON-decodes list and dict fields."""

    original_artifact = Artifact(
        id="test3",
        tags=["python", "test", "roundtrip"],
        encrypted_fields=["content", "properties"],
        metadata={"type": "test", "version": 2},
        properties={"status": "active", "priority": "high"},
    )

    # Convert to dict (should JSON-encode)
    artifact_dict = original_artifact.to_dict()

    # Convert back from dict (should JSON-decode)
    restored_artifact = Artifact.from_dict(artifact_dict)

    # Verify all data matches exactly
    if restored_artifact.tags != original_artifact.tags:
        raise AssertionError(
            f"tags don't match: {restored_artifact.tags} != {original_artifact.tags}"
        )
    if restored_artifact.encrypted_fields != original_artifact.encrypted_fields:
        raise AssertionError(
            f"encrypted_fields don't match: {restored_artifact.encrypted_fields} != {original_artifact.encrypted_fields}"
        )
    if restored_artifact.metadata != original_artifact.metadata:
        raise AssertionError(
            f"metadata don't match: {restored_artifact.metadata} != {original_artifact.metadata}"
        )
    if restored_artifact.properties != original_artifact.properties:
        raise AssertionError(
            f"properties don't match: {restored_artifact.properties} != {original_artifact.properties}"
        )

    # Verify correct types
    assert isinstance(restored_artifact.tags, list), (
        f"tags should be list, got {type(restored_artifact.tags)}"
    )
    assert isinstance(restored_artifact.encrypted_fields, list), (
        f"encrypted_fields should be list, got {type(restored_artifact.encrypted_fields)}"
    )
    assert isinstance(restored_artifact.metadata, dict), (
        f"metadata should be dict, got {type(restored_artifact.metadata)}"
    )
    assert isinstance(restored_artifact.properties, dict), (
        f"properties should be dict, got {type(restored_artifact.properties)}"
    )


def test_edge_cases():
    """Test edge cases with None values and invalid JSON."""

    # Test None values
    artifact_none = Artifact(
        id="test4", tags=None, encrypted_fields=None, metadata=None, properties=None
    )
    dict_none = artifact_none.to_dict()
    restored_none = Artifact.from_dict(dict_none)

    assert restored_none.tags is None, f"tags should be None, got {restored_none.tags}"
    assert restored_none.encrypted_fields is None, (
        f"encrypted_fields should be None, got {restored_none.encrypted_fields}"
    )
    assert restored_none.metadata is None, f"metadata should be None, got {restored_none.metadata}"
    assert restored_none.properties is None, (
        f"properties should be None, got {restored_none.properties}"
    )

    # Test invalid JSON strings (simulating corrupted database data)
    invalid_data = {
        "id": "test5",
        "tags": "invalid json [",
        "encrypted_fields": "also invalid {",
        "metadata": "not json",
        "properties": "{'python': 'dict'}",  # Python syntax, not JSON
    }

    restored_invalid = Artifact.from_dict(invalid_data)

    # Invalid JSON for lists should be wrapped in a list
    assert isinstance(restored_invalid.tags, list), (
        f"tags should be list, got {type(restored_invalid.tags)}"
    )
    assert isinstance(restored_invalid.encrypted_fields, list), (
        f"encrypted_fields should be list, got {type(restored_invalid.encrypted_fields)}"
    )
    if restored_invalid.tags != ["invalid json ["]:
        raise AssertionError(f"tags should contain the invalid string: {restored_invalid.tags}")
    if restored_invalid.encrypted_fields != ["also invalid {"]:
        raise AssertionError(
            f"encrypted_fields should contain the invalid string: {restored_invalid.encrypted_fields}"
        )

    # Invalid JSON for dicts should return None
    assert restored_invalid.metadata is None, (
        f"metadata should be None, got {restored_invalid.metadata}"
    )
    assert restored_invalid.properties is None, (
        f"properties should be None, got {restored_invalid.properties}"
    )


def test_backward_compatibility():
    """Test backward compatibility with existing string values."""

    # Simulate existing database data with string values
    legacy_data = {
        "id": "test6",
        "tags": "tag1,tag2,tag3",  # Legacy comma-separated format
        "encrypted_fields": "field1,field2",  # Legacy comma-separated format
        "metadata": '{"key": "value"}',  # JSON string (current format)
        "properties": '{"prop": "value"}',  # JSON string (current format)
    }

    restored_legacy = Artifact.from_dict(legacy_data)

    # String values for lists should be treated as single items in a list (safer than splitting)
    assert isinstance(restored_legacy.tags, list), (
        f"tags should be list, got {type(restored_legacy.tags)}"
    )
    assert isinstance(restored_legacy.encrypted_fields, list), (
        f"encrypted_fields should be list, got {type(restored_legacy.encrypted_fields)}"
    )
    if restored_legacy.tags != ["tag1,tag2,tag3"]:
        raise AssertionError(f"tags should contain the whole string: {restored_legacy.tags}")
    if restored_legacy.encrypted_fields != ["field1,field2"]:
        raise AssertionError(
            f"encrypted_fields should contain the whole string: {restored_legacy.encrypted_fields}"
        )

    # JSON strings for dicts should be decoded properly
    assert isinstance(restored_legacy.metadata, dict), (
        f"metadata should be dict, got {type(restored_legacy.metadata)}"
    )
    assert isinstance(restored_legacy.properties, dict), (
        f"properties should be dict, got {type(restored_legacy.properties)}"
    )
    if restored_legacy.metadata != {"key": "value"}:
        raise AssertionError(f"metadata should be decoded: {restored_legacy.metadata}")
    if restored_legacy.properties != {"prop": "value"}:
        raise AssertionError(f"properties should be decoded: {restored_legacy.properties}")


def main():
    """Run all tests."""

    tests = [
        test_no_in_place_mutation,
        test_json_encoding_for_lists,
        test_json_decoding_roundtrip,
        test_edge_cases,
        test_backward_compatibility,
    ]

    passed = 0
    total = len(tests)

    for test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception:
            pass

    if passed == total:
        pass
    else:
        pass

    return passed == total


if __name__ == "__main__":
    sys.exit(0 if main() else 1)

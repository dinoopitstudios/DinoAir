from datetime import datetime

import pytest

from ..sql import enforce_limit, normalize_like_pattern, parameterize_delete_older_than


def test_enforce_limit_basic_clamping():
    # valid within bounds
    assert enforce_limit(5, 10) == 5
    # negative -> clamps to 1
    assert enforce_limit(-3, 10) == 1
    # zero -> clamps to 1
    assert enforce_limit(0, 10) == 1
    # above max -> clamps to max
    assert enforce_limit(999, 10) == 10
    # non-int -> defaults to max
    assert enforce_limit("not-an-int", 7) == 7

    with pytest.raises(ValueError):
        enforce_limit(5, 0)


@pytest.mark.parametrize(
    ("raw", "expected_param"),
    [
        ("alice", "%alice%"),
        ("a%_b", "%a\\%\\_b%"),
        ("back\\slash", "%back\\\\slash%"),
        ("", "%%"),
    ],
    ids=["plain", "wildcards", "backslash", "empty"],
)
def test_normalize_like_pattern_escapes_and_wraps(raw, expected_param):
    placeholder, params = normalize_like_pattern(raw)
    assert placeholder == "?"
    assert isinstance(params, tuple)
    assert len(params) == 1
    assert params[0] == expected_param


def test_parameterize_delete_older_than_builds_sql_and_param():
    sql, params = parameterize_delete_older_than("watchdog_metrics", "timestamp", days=3)
    assert sql == "DELETE FROM watchdog_metrics WHERE timestamp < ?"
    assert isinstance(params, tuple)
    assert len(params) == 1
    # param must be ISO-parseable and represent a past time
    cutoff = datetime.fromisoformat(params[0])
    assert cutoff <= datetime.now()

    # identifiers must be validated (reject dangerous)
    with pytest.raises(ValueError):
        parameterize_delete_older_than("notes; DROP TABLE", "timestamp")
    with pytest.raises(ValueError):
        parameterize_delete_older_than("watchdog_metrics", "time-stamp")

from datetime import datetime

import pytest

from ..sql import enforce_limit, normalize_like_pattern, parameterize_delete_older_than


def test_enforce_limit_basic_clamping():
    # valid within bounds
    if enforce_limit(5, 10) != 5:
        raise AssertionError
    # negative -> clamps to 1
    if enforce_limit(-3, 10) != 1:
        raise AssertionError
    # zero -> clamps to 1
    if enforce_limit(0, 10) != 1:
        raise AssertionError
    # above max -> clamps to max
    if enforce_limit(999, 10) != 10:
        raise AssertionError
    # non-int -> defaults to max
    if enforce_limit("not-an-int", 7) != 7:
        raise AssertionError

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
    if placeholder != "?":
        raise AssertionError
    assert isinstance(params, tuple)
    assert len(params) == 1
    if params[0] != expected_param:
        raise AssertionError


def test_parameterize_delete_older_than_builds_sql_and_param():
    sql, params = parameterize_delete_older_than("watchdog_metrics", "timestamp", days=3)
    if sql != "DELETE FROM watchdog_metrics WHERE timestamp < ?":
        raise AssertionError
    assert isinstance(params, tuple)
    assert len(params) == 1
    # param must be ISO-parseable and represent a past time
    cutoff = datetime.fromisoformat(params[0])
    if cutoff > datetime.now():
        raise AssertionError

    # identifiers must be validated (reject dangerous)
    with pytest.raises(ValueError):
        parameterize_delete_older_than("notes; DROP TABLE", "timestamp")
    with pytest.raises(ValueError):
        parameterize_delete_older_than("watchdog_metrics", "time-stamp")

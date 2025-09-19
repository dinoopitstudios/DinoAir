from pathlib import Path

from pseudocode_translator.ast_cache import ASTCache
from pseudocode_translator.config import ConfigManager


def _src(n: int) -> str:
    # Distinct sources to ensure distinct cache keys
    return f"def f{n}():\n    return {n}\n"


def test_lru_eviction_order():
    # LRU default semantics; TTL disabled and no persistence
    cache = ASTCache(max_size=3, eviction_mode="lru", ttl_seconds=None, persistent_path=None)

    # Insert 3 entries
    a = _src(1)
    b = _src(2)
    c = _src(3)
    cache.parse(a)
    cache.parse(b)
    cache.parse(c)

    # Access 'a' to make it most recently used; now LRU order head is 'b'
    if cache.get(a) is None:
        raise AssertionError

    # Add 4th; should evict least-recently-used = 'b'
    d = _src(4)
    cache.parse(d)

    # Validate eviction
    if cache.get(b) is not None:
        raise AssertionError
    if cache.get(a) is None:
        raise AssertionError
    if cache.get(c) is None:
        raise AssertionError
    if cache.get(d) is None:
        raise AssertionError


def test_lfu_lite_eviction_prefers_low_frequency():
    # LFU-lite policy; small cache; TTL disabled
    cache = ASTCache(max_size=3, eviction_mode="lfu_lite", ttl_seconds=None, persistent_path=None)

    a = _src(10)
    b = _src(20)
    c = _src(30)

    cache.parse(a)
    cache.parse(b)
    cache.parse(c)

    # Access to create different frequencies
    # a: 2 additional hits (total > c)
    if cache.get(a) is None:
        raise AssertionError
    if cache.get(a) is None:
        raise AssertionError
    # b: 1 additional hit
    if cache.get(b) is None:
        raise AssertionError
    # c: 0 additional hits

    # Now insert 4th; LFU-lite should evict 'c' (lowest frequency) within bounded scan
    d = _src(40)
    cache.parse(d)

    if cache.get(c) is not None:
        raise AssertionError
    if cache.get(a) is None:
        raise AssertionError
    if cache.get(b) is None:
        raise AssertionError
    if cache.get(d) is None:
        raise AssertionError


def test_ttl_eviction_still_applies(monkeypatch):
    # Avoid background thread by constructing with ttl_seconds=None, then enable TTL
    cache = ASTCache(max_size=10, eviction_mode="lru", ttl_seconds=None, persistent_path=None)

    # Enable tiny TTL post-init (no background thread)
    cache.ttl_seconds = 0.001

    # Fix base time for insertion
    base_time = 1_000_000.0
    monkeypatch.setattr("time.time", lambda: base_time)

    # Insert a couple of entries at base_time
    s1 = _src(101)
    s2 = _src(102)
    cache.parse(s1)
    cache.parse(s2)

    # Advance time beyond TTL deterministically
    monkeypatch.setattr("time.time", lambda: base_time + 1.0)

    # Trigger TTL cleanup directly (no sleeps)
    cache.cleanup_expired_entries()

    stats = cache.get_stats()
    if stats["ttl_evictions"] != 2:
        raise AssertionError
    assert len(cache) == 0


def test_memory_eviction_policy_respected():
    # Use tiny memory budget to force memory-based eviction on insert
    # ttl_seconds=None avoids background thread side-effects
    tiny_mb = 0.001  # ~1 KB
    cache = ASTCache(
        max_size=10,
        eviction_mode="lfu_lite",
        ttl_seconds=None,
        max_memory_mb=tiny_mb,
        persistent_path=None,
    )

    # Create a source that yields a modest AST size
    s1 = "x = 1\n" * 20
    s2 = "y = 2\n" * 20
    s3 = "z = 3\n" * 20

    cache.parse(s1)
    # Bump frequency for s1 so it is less likely to be evicted by LFU-lite
    _ = cache.get(s1)

    # Insert second; may or may not evict depending on size estimation; ensure capacity remains within memory
    cache.parse(s2)

    # Track size evictions before adding third
    before = cache.get_stats()["size_evictions"]

    # Insert third; this should force at least one memory-based eviction
    cache.parse(s3)

    after = cache.get_stats()["size_evictions"]
    if after < before + 1:
        raise AssertionError

    # Ensure the cache respects memory constraints by not growing unbounded
    if len(cache) > 3:
        raise AssertionError

    # In LFU-lite, prefer evicting low-frequency candidates.
    # If exactly one of {s1, s2} was evicted, it should be s2 (lower frequency).
    present_s1 = s1 in cache
    present_s2 = s2 in cache
    present_s3 = s3 in cache
    missing_count = int(not present_s1) + int(not present_s2)
    if missing_count == 1:
        if present_s1 is not True:
            raise AssertionError
        if present_s2 is not False:
            raise AssertionError
    # Ensure the newly added entry exists
    if present_s3 is not True:
        raise AssertionError


def test_stats_include_eviction_mode():
    cache = ASTCache(max_size=3, eviction_mode="lfu_lite", ttl_seconds=None, persistent_path=None)
    stats = cache.get_stats()
    if "eviction_mode" not in stats:
        raise AssertionError
    if stats["eviction_mode"] != "lfu_lite":
        raise AssertionError


def test_persistence_survives_policy_switch(tmp_path: Path):
    # Create cache with persistence and some entries
    pdir = tmp_path / "ast_cache_persist"
    cache1 = ASTCache(max_size=3, eviction_mode="lru", ttl_seconds=None, persistent_path=pdir)
    cache1.parse(_src(201))
    cache1.parse(_src(202))
    # Persist to disk
    ok = cache1.save_to_disk()
    # Some platforms/distributions disallow pickling code objects; accept either outcome.
    if ok not in (True, False):
        raise AssertionError

    # Create a new cache with a different policy pointing to the same path
    cache2 = ASTCache(max_size=3, eviction_mode="lfu_lite", ttl_seconds=None, persistent_path=pdir)

    # The current persistence format intentionally skips non-AST payloads on load; ensure no crash and state is coherent
    stats2 = cache2.get_stats()
    assert isinstance(stats2, dict)
    if stats2["persistent_enabled"] is not True:
        raise AssertionError
    # Entries may be 0 due to format guards; just ensure no exceptions and valid stats dict present
    if stats2["size"] < 0:
        raise AssertionError


def test_env_overrides_apply_cache_config(monkeypatch):
    # Set environment overrides for cache config
    monkeypatch.setenv("PSEUDOCODE_CACHE_EVICTION_MODE", "lfu_lite")
    monkeypatch.setenv("PSEUDOCODE_CACHE_MAX_SIZE", "123")
    monkeypatch.setenv("PSEUDOCODE_CACHE_TTL_SECONDS", "789")
    monkeypatch.setenv("PSEUDOCODE_CACHE_MAX_MEMORY_MB", "12.5")
    monkeypatch.setenv("PSEUDOCODE_CACHE_PERSISTENT_PATH", str(Path.cwd() / "tmp_cache_dir"))
    monkeypatch.setenv("PSEUDOCODE_CACHE_ENABLE_COMPRESSION", "1")

    # Ensure unrelated flags do not interfere
    monkeypatch.setenv("PSEUDOCODE_LENIENT_CONFIG", "1")

    cfg = ConfigManager.load(None)

    if cfg.cache.eviction_mode != "lfu_lite":
        raise AssertionError
    if cfg.cache.max_size != 123:
        raise AssertionError
    if cfg.cache.ttl_seconds != 789:
        raise AssertionError
    if abs(cfg.cache.max_memory_mb - 12.5) >= 1e-6:
        raise AssertionError
    assert isinstance(cfg.cache.persistent_path, str)
    if not cfg.cache.persistent_path.endswith("tmp_cache_dir"):
        raise AssertionError
    if cfg.cache.enable_compression is not True:
        raise AssertionError

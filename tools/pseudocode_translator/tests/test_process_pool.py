import time

import pytest
from pseudocode_translator.config import ConfigManager, TranslatorConfig
from pseudocode_translator.execution.process_pool import ParseValidateExecutor
from pseudocode_translator.integration.events import EventDispatcher, EventHandler, EventType
from pseudocode_translator.parser import ParserModule
from pseudocode_translator.translator import TranslationManager


# Top-level slow worker (must be pickleable for Windows spawn)
def slow_parse_worker(text: str):
    t0 = time.perf_counter()
    # Return a normal parse after delay so the function is valid if it ever completes
    parser = ParserModule()
    return parser.get_parse_result(text)


def _collecting_handler(events_out):
    def _handle(event):
        events_out.append(event)

    return EventHandler(_handle)


def _events_of(events, *types):
    type_set = set(types)
    return [e for e in events if e.type in type_set]


@pytest.fixture
def manager_mock_config():
    cfg = TranslatorConfig()
    cfg.enable_plugins = False
    # Deterministic local model to avoid any network calls via LLM-first path
    cfg.llm.model_type = "mock"
    return cfg


def test_pool_disabled_uses_inprocess(manager_mock_config, monkeypatch):
    # Disable pool feature
    manager_mock_config.execution.process_pool_enabled = False

    manager = TranslationManager(manager_mock_config)
    try:
        # Guard to ensure we never initialize the pool
        def _boom():
            raise AssertionError("Pool should not be initialized when disabled")

        monkeypatch.setattr(manager, "_ensure_exec_pool", _boom, raising=True)

        # Collect events
        events = []
        handler = _collecting_handler(events)
        manager.get_event_dispatcher().register(handler)

        text = "Define a function add(a, b) that returns their sum.\n\ndef add(a, b):\n    return a + b\n"

        # Parse should be in-process
        res = manager._maybe_offload_parse(text)  # private helper under test
        assert res is not None
        # No EXEC_POOL_* events should be emitted
        pool_events = _events_of(
            events,
            EventType.EXEC_POOL_STARTED,
            EventType.EXEC_POOL_TASK_SUBMITTED,
            EventType.EXEC_POOL_TASK_COMPLETED,
            EventType.EXEC_POOL_TIMEOUT,
            EventType.EXEC_POOL_FALLBACK,
        )
        assert len(pool_events) == 0
    finally:
        manager.shutdown()


def test_pool_parse_submit_and_complete(manager_mock_config):
    # Enable pool feature
    manager_mock_config.execution.process_pool_enabled = True
    manager_mock_config.execution.process_pool_target = "parse_validate"
    manager_mock_config.execution.process_pool_task_timeout_ms = 2000
    manager = TranslationManager(manager_mock_config)
    try:
        events = []
        handler = _collecting_handler(events)
        manager.get_event_dispatcher().register(handler)

        text = "x = 1\ny = 2\nz = x + y\n"
        res = manager._maybe_offload_parse(text)
        assert res is not None

        # Expect SUBMITTED and COMPLETED lifecycle
        submitted = any(e.type == EventType.EXEC_POOL_TASK_SUBMITTED for e in events)
        completed = any(e.type == EventType.EXEC_POOL_TASK_COMPLETED for e in events)
        assert submitted is True
        assert completed is True
    finally:
        manager.shutdown()


def test_pool_timeout_then_retry_then_fallback(manager_mock_config, monkeypatch):
    # Configure aggressive timeout, enable retry-on-timeout with small limit
    manager_mock_config.execution.process_pool_enabled = True
    manager_mock_config.execution.process_pool_task_timeout_ms = 10  # 10ms to force timeout
    manager_mock_config.execution.process_pool_retry_on_timeout = True
    manager_mock_config.execution.process_pool_retry_limit = 1
    manager_mock_config.execution.process_pool_target = "parse_validate"

    manager = TranslationManager(manager_mock_config)
    try:
        # Inject slow parse function into manager seam for deterministic timeout
        manager._exec_pool_test_parse_fn = slow_parse_worker

        events = []
        handler = _collecting_handler(events)
        manager.get_event_dispatcher().register(handler)

        text = "a = 1\nb = 2\n"
        # Should fallback to in-process without raising
        res = manager._maybe_offload_parse(text)
        assert res is not None

        # Expect TIMEOUT and FALLBACK emitted
        timeout_seen = any(e.type == EventType.EXEC_POOL_TIMEOUT for e in events)
        fallback_seen = any(e.type == EventType.EXEC_POOL_FALLBACK for e in events)
        assert timeout_seen is True
        assert fallback_seen is True
    finally:
        manager.shutdown()


def test_job_size_cap_triggers_fallback(manager_mock_config):
    manager_mock_config.execution.process_pool_enabled = True
    manager_mock_config.execution.process_pool_job_max_chars = 5  # force cap
    manager_mock_config.execution.process_pool_target = "parse_validate"

    manager = TranslationManager(manager_mock_config)
    try:
        events = []
        handler = _collecting_handler(events)
        manager.get_event_dispatcher().register(handler)

        text = "this_is_longer_than_cap"
        res = manager._maybe_offload_parse(text)
        assert res is not None  # in-process fallback result

        # FALLBACK reason should be job_too_large; ensure we did NOT submit
        fallbacks = [e for e in events if e.type == EventType.EXEC_POOL_FALLBACK]
        assert any(e.data.get("reason") == "job_too_large" for e in fallbacks)
        submits = [e for e in events if e.type == EventType.EXEC_POOL_TASK_SUBMITTED]
        assert len(submits) == 0
    finally:
        manager.shutdown()


def test_events_emitted_for_lifecycle():
    # Use executor directly to verify STARTED, SUBMITTED, COMPLETED
    from pseudocode_translator.config import ExecutionConfig  # local to avoid cycles

    exec_cfg = ExecutionConfig(
        process_pool_enabled=True,
        process_pool_target="parse_only",
        process_pool_task_timeout_ms=2000,
    )
    dispatcher = EventDispatcher(async_mode=False)
    events = []
    handler = _collecting_handler(events)
    dispatcher.register(handler)

    ex = ParseValidateExecutor(exec_cfg, dispatcher=dispatcher)
    try:
        fut = ex.submit_parse("x = 1\n")
        res = fut.result()
        assert res is not None

        # Validate lifecycle emissions and payload basics
        assert any(e.type == EventType.EXEC_POOL_STARTED for e in events)
        assert any(e.type == EventType.EXEC_POOL_TASK_SUBMITTED for e in events)
        completes = [e for e in events if e.type == EventType.EXEC_POOL_TASK_COMPLETED]
        assert len(completes) >= 1
        # payload keys
        for e in completes:
            assert "kind" in e.data
            assert "duration_ms" in e.data
    finally:
        ex.shutdown()


def test_env_overrides_applied(monkeypatch, tmp_path):
    # Ensure a clean env surface; set overrides and load config
    monkeypatch.setenv("PSEUDOCODE_EXEC_POOL_ENABLED", "1")
    monkeypatch.setenv("PSEUDOCODE_EXEC_POOL_MAX_WORKERS", "3")
    monkeypatch.setenv("PSEUDOCODE_EXEC_POOL_TARGET", "validate_only")
    monkeypatch.setenv("PSEUDOCODE_EXEC_POOL_TIMEOUT_MS", "1234")
    monkeypatch.setenv("PSEUDOCODE_EXEC_POOL_JOB_MAX_CHARS", "777")
    monkeypatch.setenv("PSEUDOCODE_EXEC_POOL_RETRY_ON_TIMEOUT", "yes")
    monkeypatch.setenv("PSEUDOCODE_EXEC_POOL_RETRY_LIMIT", "2")
    monkeypatch.setenv("PSEUDOCODE_EXEC_POOL_START_METHOD", "spawn")

    cfg = ConfigManager.load(None)
    # Verify applied
    assert cfg.execution.process_pool_enabled is True
    assert cfg.execution.process_pool_max_workers == 3
    assert cfg.execution.process_pool_target == "validate_only"
    assert cfg.execution.process_pool_task_timeout_ms == 1234
    assert cfg.execution.process_pool_job_max_chars == 777
    assert cfg.execution.process_pool_retry_on_timeout is True
    assert cfg.execution.process_pool_retry_limit == 2
    assert cfg.execution.process_pool_start_method == "spawn"

# Process pool offload (opt-in)

1. Overview

- What it does: Offloads CPU-bound parse and validate work to a multiprocessing pool to utilize multiple cores. This can improve throughput and stabilize latency on large or complex inputs where parsing/validation dominates runtime. The executor is implemented in [pseudocode_translator/execution/process_pool.py](pseudocode_translator/execution/process_pool.py) and integrated in the manager via [ParseValidateExecutor](pseudocode_translator/execution/process_pool.py:59) and [TranslationManager.\_ensure_exec_pool()](pseudocode_translator/translator.py:178).
- Status: Experimental and opt-in. The default is off. No API changes are required; enabling the feature is purely configuration-driven.

2. Enabling the feature

- Config file (recommended)
  - Set [ExecutionConfig.process_pool_enabled](pseudocode_translator/config.py:345) to true. Optionally tune other [ExecutionConfig](pseudocode_translator/config.py) fields:
    ```yaml
    # ~/.pseudocode_translator/config.yaml
    execution:
      process_pool_enabled: true
      process_pool_target: parse_validate # parse_validate | parse_only | validate_only
      process_pool_task_timeout_ms: 3000 # shorter timeout to surface retries/fallbacks quicker
      process_pool_max_workers: 4 # optional; default resolves from CPU count
    ```
  - Relevant fields for quick reference:
    - [ExecutionConfig.process_pool_enabled](pseudocode_translator/config.py:345)
    - [ExecutionConfig.process_pool_max_workers](pseudocode_translator/config.py:346)
    - [ExecutionConfig.process_pool_target](pseudocode_translator/config.py:347)
    - [ExecutionConfig.process_pool_task_timeout_ms](pseudocode_translator/config.py:350)
    - [ExecutionConfig.process_pool_job_max_chars](pseudocode_translator/config.py:351)
    - [ExecutionConfig.process_pool_start_method](pseudocode_translator/config.py:354)
    - [ExecutionConfig.process_pool_retry_on_timeout](pseudocode_translator/config.py:357)
    - [ExecutionConfig.process_pool_retry_limit](pseudocode_translator/config.py:358)
- Environment overrides (opt-in per run)
  - Exact names (recognized in [Config.\_collect_env_overrides](pseudocode_translator/config.py:495) and mapped by [Config.\_normalize_override_key](pseudocode_translator/config.py:533)):
    - PSEUDOCODE_EXEC_POOL_ENABLED
    - PSEUDOCODE_EXEC_POOL_MAX_WORKERS
    - PSEUDOCODE_EXEC_POOL_TARGET
    - PSEUDOCODE_EXEC_POOL_TIMEOUT_MS
    - PSEUDOCODE_EXEC_POOL_JOB_MAX_CHARS
    - PSEUDOCODE_EXEC_POOL_RETRY_ON_TIMEOUT
    - PSEUDOCODE_EXEC_POOL_RETRY_LIMIT
    - PSEUDOCODE_EXEC_POOL_START_METHOD
- Precedence
  - Defaults < file < env. See precedence in [ConfigManager.load](pseudocode_translator/config.py:773) where defaults are built, a file (if present) is merged, then env overrides are applied last.

3. Configuration reference

- All fields live under execution.\* ([ExecutionConfig](pseudocode_translator/config.py)).
- Defaults and behavior:
  | Field | Default | Description |
  |---|---|---|
  | process_pool_enabled | False | Feature flag for offloading parse/validate to a process pool. When false, all work remains in-process. |
  | process_pool_max_workers | None | If None, resolves at runtime to max(2, os.cpu_count() or 2). |
  | process_pool_target | "parse_validate" | What to offload: "parse_validate", "parse_only", or "validate_only". Non-targeted operations run in-process. |
  | process_pool_task_timeout_ms | 5000 | Per-task timeout used by the Future result wrapper. On timeout, emits an event and may retry (see retry fields). |
  | process_pool_job_max_chars | 50000 | Max size for parse jobs. Larger jobs bypass the pool and run in-process. |
  | process_pool_start_method | None | Process start method. None uses platform default; Windows prefers "spawn" (see [ParseValidateExecutor.\_resolve_start_method()](pseudocode_translator/execution/process_pool.py:96)). |
  | process_pool_retry_on_timeout | True | Whether to retry once on timeout/broken pool, with pool restart. |
  | process_pool_retry_limit | 1 | Retry attempts on timeout/broken pool. Default is a single retry. |
- Validation behavior
  - Config validation enforces allowed targets and positive numeric ranges in [ExecutionConfig.validate](pseudocode_translator/config.py:360). The manager uses lenient validation by default; runtime guards apply (timeouts, job size cap, retry/fallback). Values may be clamped to safe ranges internally where applicable.

4. Guardrails and behavior

- Timeouts and retry
  - Each task waits up to process_pool_task_timeout_ms. On timeout or a broken pool, a timeout event is emitted, the pool is restarted, and a single retry is attempted by default; on further failure, a safe fallback is taken. See retry loop in [ParseValidateExecutor.\_TaskHandle.result()](pseudocode_translator/execution/process_pool.py:203).
- Fallbacks are safe and transparent
  - If retry is exhausted or a guardrail triggers, the system falls back to in-process parsing/validation without surfacing user-facing errors. Immediate "do not offload" conditions are signaled via an internal marker and caught by the manager, which then runs the operation locally. See parse fallback in [TranslationManager.\_maybe_offload_parse](pseudocode_translator/translator.py:213) and validate fallback in [TranslationManager.\_maybe_offload_validate](pseudocode_translator/translator.py:250).
- Job size cap
  - Parse jobs exceeding process_pool_job_max_chars bypass the pool and run in-process; a fallback event is emitted. See cap check in [ParseValidateExecutor.submit_parse](pseudocode_translator/execution/process_pool.py:157).
- Windows-first
  - Workers are top-level pickleable functions ([worker_parse](pseudocode_translator/execution/process_pool.py:26), [worker_validate](pseudocode_translator/execution/process_pool.py:32)) and the default start method on Windows is "spawn" via [ParseValidateExecutor.\_resolve_start_method()](pseudocode_translator/execution/process_pool.py:96).

5. Events and telemetry

- Events emitted (see [EventType](pseudocode_translator/integration/events.py)):
  - EXEC_POOL_STARTED: {"max_workers","start_method"} ([EventType.EXEC_POOL_STARTED](pseudocode_translator/integration/events.py:59))
  - EXEC_POOL_TASK_SUBMITTED: {"kind","size_chars"} ([EventType.EXEC_POOL_TASK_SUBMITTED](pseudocode_translator/integration/events.py:61))
  - EXEC_POOL_TASK_COMPLETED: {"kind","duration_ms"} ([EventType.EXEC_POOL_TASK_COMPLETED](pseudocode_translator/integration/events.py:63))
  - EXEC_POOL_TIMEOUT: {"kind","timeout_ms","attempt"} ([EventType.EXEC_POOL_TIMEOUT](pseudocode_translator/integration/events.py:65))
  - EXEC_POOL_FALLBACK: {"kind","reason"} ([EventType.EXEC_POOL_FALLBACK](pseudocode_translator/integration/events.py:67))
- Telemetry (no-op unless enabled)
  - Counters: exec_pool.started, exec_pool.submit, exec_pool.complete, exec_pool.timeout, exec_pool.fallback
  - Durations: exec_pool.init_ms, exec_pool.task_ms
  - Emission sites include pool init and task lifecycle in [pseudocode_translator/execution/process_pool.py](pseudocode_translator/execution/process_pool.py). Telemetry enablement and recorder are defined in [pseudocode_translator/telemetry.py](pseudocode_translator/telemetry.py).

6. Usage examples

- Minimal config enabling parse+validate offload with a small timeout:
  ```yaml
  execution:
    process_pool_enabled: true
    process_pool_target: parse_validate
    process_pool_task_timeout_ms: 3000
  ```
- Environment-only (Windows cmd)
  ```
  set PSEUDOCODE_EXEC_POOL_ENABLED=1
  set PSEUDOCODE_EXEC_POOL_TARGET=parse_validate
  set PSEUDOCODE_EXEC_POOL_TIMEOUT_MS=3000
  ```
  Precedence reminder: env overrides win over file values (see [ConfigManager.load](pseudocode_translator/config.py:773)).

7. Benchmarking

- How to run
  - A small benchmark script is provided at [examples/process_pool_benchmark.py](examples/process_pool_benchmark.py).
  - Example commands:
    - python examples/process_pool_benchmark.py --enabled=0 --docs=200 --seed=123
    - python examples/process_pool_benchmark.py --enabled=1 --docs=200 --seed=123 --workers=4
- Output fields (JSON)
  - throughput_docs_per_s: higher is better
  - mean_ms: average per-document latency
  - p95_ms: 95th percentile latency
  - Interpret differences by comparing enabled=0 vs enabled=1 for the same workload and seed.

8. Limitations and guidance

- Overhead can outweigh benefits on small inputs or single-document runs. Prefer enabling for larger batches or heavier parse/validate workloads.
- Memory footprint increases with worker count and input size. Tune process_pool_job_max_chars and process_pool_max_workers to fit your system.
- If you observe instability or regressions, disable the feature. With [ExecutionConfig.process_pool_enabled](pseudocode_translator/config.py:345)=false (default), all behavior reverts to in-process baseline.

9. Pointers to source

- Executor and workers: [pseudocode_translator/execution/process_pool.py](pseudocode_translator/execution/process_pool.py)
- Config additions: [pseudocode_translator/config.py](pseudocode_translator/config.py)
- Event types: [pseudocode_translator/integration/events.py](pseudocode_translator/integration/events.py)
- Manager integration: [pseudocode_translator/translator.py](pseudocode_translator/translator.py)

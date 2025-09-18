# Pseudocode Translator

## API Stability and Deprecations

- API stability levels and current status: [docs/api_stability.md](docs/api_stability.md)
- Deprecation notice and migration for the legacy interface: [docs/deprecations/llm_interface.md](docs/deprecations/llm_interface.md)

Notes

- Importing [pseudocode_translator/llm_interface.py](pseudocode_translator/llm_interface.py) emits a DeprecationWarning on import. Migrate to the supported path:
  - Orchestration and translation via [pseudocode_translator/translator.py](pseudocode_translator/translator.py)
  - Model selection via [pseudocode_translator/models/model_factory.py](pseudocode_translator/models/model_factory.py)

## Adaptive chunking (experimental)

Adaptive chunking dynamically adapts streaming chunk size to improve throughput and stabilize latency. This feature is off by default and feature-flagged; when disabled, baseline fixed-size behavior is preserved.

Enable:

- Config: set [StreamingConfig.adaptive_chunking_enabled](pseudocode_translator/config.py:258) to true.
- Env: set PSEUDOCODE_STREAMING_ADAPTIVE_ENABLED=1.

See the full guide: [docs/adaptive_chunking.md](docs/adaptive_chunking.md)

API stability: Experimental. See [docs/api_stability.md](docs/api_stability.md).

## Process pool offload (opt-in)

Off by default and experimental. Offloads CPU-bound parse/validate to a multiprocessing pool to improve throughput on multi-core systems. When disabled, baseline in-process behavior is preserved.

Enable:

- Config: set [ExecutionConfig.process_pool_enabled](pseudocode_translator/config.py:345) to true.
- Env: set PSEUDOCODE_EXEC_POOL_ENABLED=1.

See the full guide: [docs/process_pool.md](docs/process_pool.md)

API stability: Experimental. See [docs/api_stability.md](docs/api_stability.md).

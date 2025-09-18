# Public API Stability

This document summarizes the stability of top-level public surfaces. Stability levels:

- Stable: Backward-compatible; subject to deprecation policy before breaking.
- Experimental: May change without notice; off by default or guarded by env/config.
- Deprecated: Supported for a limited time; see deprecation note and migrate promptly.

| Surface                                                                                                                                                                                                                                                      | Status       | Notes                                                                                                                         |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------ | ----------------------------------------------------------------------------------------------------------------------------- |
| TranslationManager in [pseudocode_translator/translator.py](../pseudocode_translator/translator.py) — key public methods: translate_pseudocode, translate_streaming, translate_text_block, get_event_dispatcher, get_telemetry_snapshot                      | Stable       | Primary API for orchestration, translation, streaming, events, and telemetry snapshot.                                        |
| Parser public API score_line_language in [pseudocode_translator/parser.py](../pseudocode_translator/parser.py)                                                                                                                                               | Stable       | Public scoring API is conservative and used by mixed/streaming separation.                                                    |
| Integration API get_info in [pseudocode_translator/integration/api.py](../pseudocode_translator/integration/api.py)                                                                                                                                          | Stable       | Provides model lists, telemetry snapshot (if enabled), and config summary.                                                    |
| ModelFactory and BaseTranslationModel interface surface in [pseudocode_translator/models/model_factory.py](../pseudocode_translator/models/model_factory.py) and [pseudocode_translator/models/base_model.py](../pseudocode_translator/models/base_model.py) | Stable       | Extend models with care; follow interface and capability metadata contract.                                                   |
| Telemetry module in [pseudocode_translator/telemetry.py](../pseudocode_translator/telemetry.py)                                                                                                                                                              | Experimental | Disabled by default; returns a no-op recorder unless PSEUDOCODE_TELEMETRY is truthy; schema and behavior may change.          |
| Plugin system and loader in [pseudocode_translator/models/plugin_system.py](../pseudocode_translator/models/plugin_system.py)                                                                                                                                | Experimental | Disabled by default; gated by PSEUDOCODE_ENABLE_PLUGINS; subject to change.                                                   |
| Legacy llm_interface in [pseudocode_translator/llm_interface.py](../pseudocode_translator/llm_interface.py)                                                                                                                                                  | Deprecated   | Use TranslationManager and ModelFactory instead; see migration: [llm_interface deprecation](./deprecations/llm_interface.md). |

## Configuration notes

- Precedence and strict validation: the configuration CLI prioritizes explicit flags over environment variables and runs strict validation by default. See [pseudocode_translator/config_tool.py](../pseudocode_translator/config_tool.py). The config_tool validate command is Stable.
- For complete configuration details, refer to the existing configuration docs in the repository.

For migration away from the legacy interface, see [Deprecation: llm_interface](./deprecations/llm_interface.md).

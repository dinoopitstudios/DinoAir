# Translator Abstractions and Refactor Guide

This document describes the internal abstractions and helpers introduced to reduce complexity in the translator while preserving behavior. It ties changes to concrete locations in the codebase and explains how to test them safely.

## Overview

The translator has been refactored incrementally to:

- Flatten deeply nested control flow without changing behavior
- Isolate cross-cutting concerns (events, offload, dependency analysis, fix-refinement)
- Reduce parameter bloat via local helpers and context

Core entry and orchestration methods remain the same, with strict parity on:

- Event types, payloads, and ordering
- Telemetry section labels and nesting
- Metadata keys and values
- Public method signatures and return types

Key orchestration locations:

- [TranslationManager.translate_pseudocode()](tools/pseudocode_translator/translator.py:337)
- [TranslationManager.\_translate_with_llm_first()](tools/pseudocode_translator/translator.py:412)
- [TranslationManager.\_translate_with_structured_parsing()](tools/pseudocode_translator/translator.py:491)
- [TranslationManager.translate_streaming()](tools/pseudocode_translator/translator.py:1322)

## New Support Modules

1. FixRefiner

- Purpose: behavior-parity refinement helper delegating to the active model
- API: [attempt_fixes()](tools/pseudocode_translator/translator_support/fix_refiner.py:19)
- Contract:
  - Uses top-3 validation errors joined by newline
  - Never raises; returns (original_code, []) on error
  - Returns (refined_code, []) when model reports success and provides code

Used by manager wrapper:

- [TranslationManager.\_attempt_fixes()](tools/pseudocode_translator/translator.py:1150) delegates to support while preserving logging and telemetry semantics

2. DependencyResolver

- Purpose: encapsulate AST walking and name/import extraction
- Class: [DependencyResolver](tools/pseudocode_translator/translator_support/dependency_resolver.py:25)
- Methods:
  - analyze_block(code: str) → {"defined_names": list[str], "required_imports": list[str]}
  - analyze_blocks(blocks) → list[dict]
- Normalization:
  - Import strings are normalized as "import x" or "from m import n"
- Used from manager:
  - [TranslationManager.\_handle_dependencies()](tools/pseudocode_translator/translator.py:993)

3. OffloadExecutor

- Purpose: unify process-pool gating, submission, timeouts, and immediate fallback sentinel handling, with consistent event emission
- Module: tools/pseudocode_translator/translator_support/offload_executor.py
- Used from manager (local imports to avoid cycles):
  - [TranslationManager.\_maybe_offload_parse()](tools/pseudocode_translator/translator.py:202)
  - [TranslationManager.\_maybe_offload_validate()](tools/pseudocode_translator/translator.py:239)

4. StreamEmitter

- Purpose: centralize streaming event emissions
- Module: tools/pseudocode_translator/translator_support/stream_emitter.py
- Used in [TranslationManager.translate_streaming()](tools/pseudocode_translator/translator.py:1322) (best-effort, local import)

## Internal Manager Helpers

To reduce complexity while preserving behavior, the following helpers were introduced inside the manager:

- Document-level LLM config:
  - [TranslationManager.\_build_model_config_for_document()](tools/pseudocode_translator/translator.py:726)

- Per-block LLM config:
  - [TranslationManager.\_build_model_config_for_block()](tools/pseudocode_translator/translator.py:714)

- Validate and optionally fix (LLM-first flow):
  - [TranslationManager.\_validate_and_optionally_fix()](tools/pseudocode_translator/translator.py:741)

- Offload parse orchestration:
  - [TranslationManager.\_parse_input_with_offload()](tools/pseudocode_translator/translator.py:774)

- Translate text with model (per-block):
  - [TranslationManager.\_translate_text_with_model()](tools/pseudocode_translator/translator.py:781)
  - Returns (translated_code_or_None, metadata_updates) and preserves error formatting for top-level ENGLISH blocks

- Block processors:
  - [TranslationManager.\_process_english_block()](tools/pseudocode_translator/translator.py:904)
  - [TranslationManager.\_process_mixed_block()](tools/pseudocode_translator/translator.py:932)
  - [TranslationManager.\_process_passthrough_block()](tools/pseudocode_translator/translator.py:961)
  - [TranslationManager.\_process_blocks()](tools/pseudocode_translator/translator.py:965) now uses a simple for loop with early-continue guards

- Structured completion orchestration:
  - Assemble wrapper: [TranslationManager.\_assemble_or_error()](tools/pseudocode_translator/translator.py:590)
  - Suggestions: [TranslationManager.\_suggest_improvements()](tools/pseudocode_translator/translator.py:628)
  - Completion: [TranslationManager.\_complete_structured_translation()](tools/pseudocode_translator/translator.py:634)

- Mixed block segmentation:
  - [TranslationManager.\_separate_mixed_block()](tools/pseudocode_translator/translator.py:1100)
  - Simpler state machine with identical thresholds and outputs

- Emission helpers (best-effort):
  - [TranslationManager.\_emit_translation_started()](tools/pseudocode_translator/translator.py:274)
  - [TranslationManager.\_emit_translation_completed()](tools/pseudocode_translator/translator.py:286)
  - [TranslationManager.\_emit_translation_failed()](tools/pseudocode_translator/translator.py:299)

## Behavior Parity and Telemetry

Strict guarantees:

- Events: TRANSLATION*STARTED, TRANSLATION_COMPLETED, TRANSLATION_FAILED, STREAM*\* unchanged (names, payload keys, sequencing)
- Telemetry sections unchanged:
  - "translate.model", "translate.validate", "translate.parse", "translate.assemble"
- Metadata keys unchanged (non-exhaustive):
  - approach, duration_ms, blocks_processed, blocks_translated, cache_hits, model_tokens_used, validation_passed, translation_id
- Public signatures and return types unchanged

## Testing

Test suites:

- Unit and smoke tests:
  - [tools/pseudocode_translator/tests](tools/pseudocode_translator/tests)
  - [tools/tests](tools/tests)

Tests for new abstractions:

- [test_new_abstractions.py](tools/pseudocode_translator/tests/test_new_abstractions.py)
  - DependencyResolver normalization and name/import extraction
  - FixRefiner: success and exception paths returning a model-like result
  - OffloadExecutor: gating plus immediate-fallback sentinel
  - \_separate_mixed_block segmentation parity using deterministic scoring
  - translate_pseudocode orchestration guard-clauses returning manager-level TranslationResult

Known pre-existing failures (stream characterization):

- [test_stream_characterization.py](tools/pseudocode_translator/tests/test_stream_characterization.py:1)
  - test_line_by_line_yields_and_events()
  - test_full_document_chunk_events_and_yields()
  - Logs typically include a missing "mock" model in registry and streaming invoker initialization nuances

How to run (Windows cmd):

```
set PYTHONPATH=%CD%\tools;%CD% && python -m pytest tools\pseudocode_translator\tests -q
set PYTHONPATH=%CD%\tools;%CD% && python -m pytest tools\tests -q
```

## Migration Guidance

- Use [TranslationManager.\_translate_text_with_model()](tools/pseudocode_translator/translator.py:781) for any new per-block translation logic rather than duplicating validation and error formatting.
- Prefer [DependencyResolver](tools/pseudocode_translator/translator_support/dependency_resolver.py:25) over ad-hoc AST code; it returns normalized import strings that downstream consumers can match robustly.
- Use [OffloadExecutor](tools/pseudocode_translator/translator_support/offload_executor.py) to unify process-pool semantics and avoid duplicated fallback paths.
- When working with streaming, prefer [StreamEmitter](tools/pseudocode_translator/translator_support/stream_emitter.py) for consistent event shapes; keep emissions in the same logical points to preserve ordering.
- For document-level translation, build config via [TranslationManager.\_build_model_config_for_document()](tools/pseudocode_translator/translator.py:726) to remain in sync with LLM-first expectations.

## Maintenance Notes

- Keep support modules (translator_support/\*) free of translator.py imports to avoid cycles.
- When extending events or telemetry, update tests to capture any externally visible changes and consider guarding with feature flags.
- If normalization formats change (e.g., for imports), reconcile with tests first to avoid surprises downstream.

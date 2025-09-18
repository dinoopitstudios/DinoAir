# Deprecation: pseudocode_translator.llm_interface

Summary

- pseudocode_translator.llm_interface is deprecated; switch to TranslationManager and ModelFactory. This module will be removed in a future release.

- Preferred APIs:
  - Orchestration and translation: [TranslationManager](../pseudocode_translator/translator.py)
  - Model selection and capabilities: [ModelFactory](../pseudocode_translator/models/model_factory.py) and [BaseTranslationModel](../pseudocode_translator/models/base_model.py)

Rationale

- Unified orchestration via TranslationManager centralizes parsing, model usage, assembly, validation, streaming, and event emission.
- Standardized model selection via ModelFactory enables capability-aware selection, aliasing, defaults, and fallbacks.
- Built-in telemetry/events and safer defaults reduce integration risk and improve observability.

Deprecation timeline

- Deprecated now.
- Removal no sooner than the next minor release after 60 days.

Runtime signal

- Importing the module emits a DeprecationWarning on import. See [llm_interface.py](../pseudocode_translator/llm_interface.py).

How to display DeprecationWarning at runtime:

- Via environment (examples):
  - Linux/macOS: PYTHONWARNINGS=default python your_script.py
  - Windows (cmd): set PYTHONWARNINGS=default && python your_script.py
- Via code:
  ```python
  import warnings
  warnings.filterwarnings("default", category=DeprecationWarning)
  import pseudocode_translator.llm_interface  # will show the warning
  ```

Migration guide

1. Direct translate calls

- Before (legacy):

  ```python
  from pseudocode_translator.config import ConfigManager
  from pseudocode_translator.llm_interface import LLMInterface  # deprecated

  cfg = ConfigManager.load()
  llm = LLMInterface(cfg.llm)
  llm.initialize_model()
  code = llm.translate("create a function to add two numbers")
  ```

- After (supported): use [translate_pseudocode()](../pseudocode_translator/translator.py:165) or [translate_text_block()](../pseudocode_translator/translator.py:1029) on [TranslationManager](../pseudocode_translator/translator.py)

  ```python
  from pseudocode_translator.config import ConfigManager, TranslatorConfig
  from pseudocode_translator.translator import TranslationManager

  cfg = ConfigManager.load()
  manager = TranslationManager(TranslatorConfig(cfg))
  result = manager.translate_pseudocode("create a function to add two numbers")
  if result.success:
      print(result.code)
  ```

2. Streaming migration

- Use [translate_streaming()](../pseudocode_translator/translator.py:1075) for bounded backpressure semantics. Events are emitted on the dispatcher (TRANSLATION*\*, STREAM*\*, MODEL_CHANGED).

  ```python
  from pseudocode_translator.config import ConfigManager, TranslatorConfig
  from pseudocode_translator.translator import TranslationManager

  cfg = ConfigManager.load()
  manager = TranslationManager(TranslatorConfig(cfg))

  assembled = []
  for chunk in manager.translate_streaming("large pseudocode input...", chunk_size=4096):
      if chunk.success and chunk.code:
          assembled.append(chunk.code)
  final_code = "".join(assembled)
  ```

- Event hooks: get dispatcher via [get_event_dispatcher()](../pseudocode_translator/translator.py:970). Telemetry snapshot via [get_telemetry_snapshot()](../pseudocode_translator/translator.py:1008).

3. Model selection and capabilities

- Prefer factory-based selection with capability filters (supported language, streaming requirement):

  - Convenience function [create_model()](../pseudocode_translator/models/model_factory.py:616)
  - Class APIs [ModelFactory.find_models_by_language()](../pseudocode_translator/models/model_factory.py:317), [ModelFactory.list_models()](../pseudocode_translator/models/model_factory.py:262)

  ```python
  from pseudocode_translator.models.base_model import OutputLanguage
  from pseudocode_translator.models.model_factory import create_model, ModelFactory

  # Language + streaming requirements
  model = create_model(require_streaming=True, language="python")

  # Listing/filtering
  python_models = ModelFactory.find_models_by_language(OutputLanguage.PYTHON)
  all_models = ModelFactory.list_models()
  ```

- Within TranslationManager, switch models at runtime with:
  ```python
  manager.switch_model("qwen")  # emits MODEL_CHANGED
  ```

Minimal mapping of legacy to supported APIs

- LLMInterface.translate → TranslationManager.[translate_pseudocode()](../pseudocode_translator/translator.py:165) or [translate_text_block()](../pseudocode_translator/translator.py:1029)
- LLMInterface.batch_translate → BaseTranslationModel.batch_translate (model-level) or orchestrate via TranslationManager loops
- LLMInterface.switch_model → TranslationManager.[switch_model()](../pseudocode_translator/translator.py:974)
- LLMInterface.get_current_model/list_available_models → TranslationManager.[get_current_model()](../pseudocode_translator/translator.py:1000)/[list_available_models()](../pseudocode_translator/translator.py:1004)
- Refinement: use BaseTranslationModel.[refine_code()](../pseudocode_translator/models/base_model.py:272) through TranslationManager internals

Testing considerations

- Import warning is covered in [pseudocode_translator/tests/test_deprecation_warning.py](../pseudocode_translator/tests/test_deprecation_warning.py). Keep the test in place to ensure the DeprecationWarning continues to be emitted until removal.

Related references

- Translation methods: [translate_pseudocode()](../pseudocode_translator/translator.py:165), [translate_text_block()](../pseudocode_translator/translator.py:1029), [translate_streaming()](../pseudocode_translator/translator.py:1075)
- Events: dispatcher via [get_event_dispatcher()](../pseudocode_translator/translator.py:970)
- Telemetry: [telemetry.py](../pseudocode_translator/telemetry.py)
- Legacy entry point: [LLMInterface](../pseudocode_translator/llm_interface.py:100)

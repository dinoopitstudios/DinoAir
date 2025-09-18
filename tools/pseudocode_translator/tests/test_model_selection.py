from pathlib import Path
from typing import Any

from pseudocode_translator.models.base_model import (
    BaseTranslationModel,
    ModelCapabilities,
    ModelMetadata,
    OutputLanguage,
    TranslationConfig,
    TranslationResult,
)
from pseudocode_translator.models.model_factory import ModelFactory


class _TestModelBase(BaseTranslationModel):
    @property
    def metadata(self) -> ModelMetadata:
        # Keep this simple; selection relies on get_capabilities(), not metadata
        return ModelMetadata(
            name=self.__class__.__name__.lower(),
            version="0.0.0",
            supported_languages=list(OutputLanguage),
            description="Test model",
            author="test",
            license="MIT",
            model_type="test",
            size_gb=0.0,
            requires_gpu=False,
            supports_streaming=False,
            max_context_length=2048,
        )

    @property
    def capabilities(self) -> ModelCapabilities:
        # Not used by selection; present for compatibility
        return ModelCapabilities()

    def initialize(self, model_path: Path | None = None, **kwargs) -> None:
        self._initialized = True

    def translate(
        self,
        instruction: str,
        config: TranslationConfig | None = None,
        context: dict[str, Any] | None = None,
    ) -> TranslationResult:
        if not self._initialized:
            raise RuntimeError("Model not initialized")
        cfg = config or TranslationConfig()
        return TranslationResult(
            success=True,
            code="# test",
            language=cfg.target_language,
            confidence=1.0,
        )

    def validate_input(self, instruction: str) -> tuple[bool, str | None]:
        return True, None


# Streaming and non-streaming python-capable models
class _StreamingPythonModel(_TestModelBase):
    def get_capabilities(self) -> dict[str, Any]:
        return {
            "supports_streaming": True,
            "supported_languages": ["python"],
            "tokens_per_second": (1000, 2000),
            "quality": "base",
        }


class _NonStreamingPythonModel(_TestModelBase):
    def get_capabilities(self) -> dict[str, Any]:
        return {
            "supports_streaming": False,
            "supported_languages": ["python"],
            "tokens_per_second": (1000, 2000),
            "quality": "base",
        }


# Language-filtered models
class _JavaOnlyModel(_TestModelBase):
    def get_capabilities(self) -> dict[str, Any]:
        return {
            "supports_streaming": False,
            "supported_languages": ["java"],
            "tokens_per_second": (500, 600),
            "quality": "base",
        }


class _PythonOnlyModel(_TestModelBase):
    def get_capabilities(self) -> dict[str, Any]:
        return {
            "supports_streaming": False,
            "supported_languages": ["python"],
            "tokens_per_second": (500, 600),
            "quality": "base",
        }


# Same quality, different TPS
class _BaseSlowStreaming(_TestModelBase):
    def get_capabilities(self) -> dict[str, Any]:
        return {
            "supports_streaming": True,
            "supported_languages": ["python"],
            "tokens_per_second": (50, 100),
            "quality": "base",
        }


class _BaseFastStreaming(_TestModelBase):
    def get_capabilities(self) -> dict[str, Any]:
        return {
            "supports_streaming": True,
            "supported_languages": ["python"],
            "tokens_per_second": (2000, 4000),
            "quality": "base",
        }


def _fresh_registry():
    # Ensure a clean registry for each test
    ModelFactory.clear_registry()
    # Ensure factory is initialized without auto-discovery
    ModelFactory.initialize(auto_discover=False)


def test_factory_prefers_streaming_capable_when_required():
    _fresh_registry()
    # Register candidates
    ModelFactory.register_model(_NonStreamingPythonModel, name="py_ns", aliases=[], is_default=True)
    ModelFactory.register_model(_StreamingPythonModel, name="py_stream", aliases=[])

    # Request requires streaming True
    model = ModelFactory.create_model(require_streaming=True, language="python")
    caps = model.get_capabilities()
    if caps["supports_streaming"] is not True:
        raise AssertionError("Factory should prefer a streaming-capable model when required")


def test_factory_filters_by_supported_language():
    _fresh_registry()
    # Register language-specific candidates
    ModelFactory.register_model(_JavaOnlyModel, name="java_only", aliases=[], is_default=True)
    ModelFactory.register_model(_PythonOnlyModel, name="python_only", aliases=[])

    # language=python should select python-capable model
    model_py = ModelFactory.create_model(language="python")
    caps_py = model_py.get_capabilities()
    if "python" not in [l.lower() for l in caps_py["supported_languages"]]:
        raise AssertionError("Factory should select a model that supports Python")

    # language=java should select java-capable model
    model_java = ModelFactory.create_model(language="java")
    caps_java = model_java.get_capabilities()
    if "java" not in [l.lower() for l in caps_java["supported_languages"]]:
        raise AssertionError("Factory should select a model that supports Java")


def test_factory_prefers_higher_quality_or_tps():
    _fresh_registry()
    # Two streaming, python-capable models with same quality but different TPS
    ModelFactory.register_model(_BaseSlowStreaming, name="slow_stream", aliases=[], is_default=True)
    ModelFactory.register_model(_BaseFastStreaming, name="fast_stream", aliases=[])

    model = ModelFactory.create_model(require_streaming=True, language="python")
    # Expect fast_stream due to higher tokens_per_second
    assert isinstance(model, _BaseFastStreaming), (
        "Factory should prefer higher TPS when quality is the same"
    )

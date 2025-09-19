"""
Translation Pipeline Coordinator

This module provides a clean, orchestrated approach to managing the translation
workflow, replacing the monolithic TranslationManager with focused coordination.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from ..models.base_model import OutputLanguage
from .dependency_container import DependencyContainer
from .error_handler import ErrorCategory, ErrorHandler

if TYPE_CHECKING:
    from ..config import TranslatorConfig

logger = logging.getLogger(__name__)


@dataclass
class TranslationContext:
    """Context information for a translation operation."""

    translation_id: int
    start_time: float
    target_language: OutputLanguage
    input_text: str
    metadata: dict[str, Any]

    def __post_init__(self):
        if not self.metadata:
            self.metadata = {}


@dataclass
class TranslationResult:
    """Result of a translation operation."""

    success: bool
    code: str | None
    errors: list[str]
    warnings: list[str]
    metadata: dict[str, Any]

    def __post_init__(self):
        if not self.errors:
            self.errors = []
        if not self.warnings:
            self.warnings = []
        if not self.metadata:
            self.metadata = {}

    @property
    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return len(self.warnings) > 0


class TranslationPipeline:
    """
    Coordinates the translation pipeline workflow.

    This class orchestrates the translation process by delegating to specialized
    services while maintaining a clean separation of concerns.
    """

    def __init__(self, config: TranslatorConfig, container: DependencyContainer | None = None):
        self.config = config
        self.container = container or DependencyContainer()
        self.error_handler = ErrorHandler(logger_name=__name__)

        # Translation counter for unique IDs
        self._translation_counter = 0

        # Initialize services
        self._initialize_services()

        logger.info("Translation Pipeline initialized")

    def translate(
        self, input_text: str, target_language: OutputLanguage | None = None
    ) -> TranslationResult:
        """
        Translate pseudocode to the target language.

        Args:
            input_text: The pseudocode text to translate
            target_language: Target programming language

        Returns:
            TranslationResult containing the translated code and metadata
        """
        # Create translation context
        context = self._create_translation_context(input_text, target_language)

        try:
            # Emit translation started event
            self._emit_event(
                "translation_started",
                {
                    "id": context.translation_id,
                    "mode": "pipeline",
                    "target_language": context.target_language.value,
                },
            )

            # Try LLM-first approach
            llm_result = self._try_llm_first_translation(context)
            if llm_result and llm_result.success:
                self._emit_event(
                    "translation_completed",
                    {"id": context.translation_id, "approach": "llm_first", "success": True},
                )
                return llm_result

            # Fallback to structured parsing approach
            logger.info("LLM-first failed, falling back to structured parsing")
            structured_result = self._try_structured_translation(context)

            if structured_result and structured_result.success:
                self._emit_event(
                    "translation_completed",
                    {
                        "id": context.translation_id,
                        "approach": "structured_parsing",
                        "success": True,
                    },
                )
            else:
                self._emit_event(
                    "translation_failed",
                    {"id": context.translation_id, "error": "Both translation approaches failed"},
                )

            return structured_result or self._create_failure_result(
                context, "All translation approaches failed"
            )

        except Exception as e:
            error_info = self.error_handler.handle_exception(
                e, ErrorCategory.TRANSLATION, additional_context="Pipeline execution"
            )

            self._emit_event("translation_failed", {"id": context.translation_id, "error": str(e)})

            return TranslationResult(
                success=False,
                code=None,
                errors=[self.error_handler.format_error_message(error_info)],
                warnings=[],
                metadata=self._create_metadata(context, 0, 0, False),
            )

    def _create_translation_context(
        self, input_text: str, target_language: OutputLanguage | None
    ) -> TranslationContext:
        """Create context for a new translation operation."""
        self._translation_counter += 1

        return TranslationContext(
            translation_id=self._translation_counter,
            start_time=time.time(),
            target_language=target_language or OutputLanguage.PYTHON,
            input_text=input_text,
            metadata={},
        )

    def _try_llm_first_translation(self, context: TranslationContext) -> TranslationResult | None:
        """Attempt LLM-first translation approach."""
        try:
            # TODO: Implement LLM-first service resolution when services are created
            logger.debug("Attempting LLM-first translation")
            logger.warning("LLM-first translation not yet implemented in new architecture")
            return None

        except Exception as e:
            self.error_handler.handle_exception(
                e, ErrorCategory.TRANSLATION, additional_context="LLM-first approach"
            )
            logger.warning("LLM-first translation failed: %s", str(e))
            return None

    def _try_structured_translation(self, context: TranslationContext) -> TranslationResult | None:
        """Attempt structured parsing translation approach."""
        try:
            # TODO: Implement structured translation service resolution when services are created
            logger.debug("Attempting structured parsing translation")
            logger.warning("Structured translation not yet implemented in new architecture")

            # Return a placeholder successful result for now
            return TranslationResult(
                success=True,
                code="# Placeholder: Structured translation not yet implemented",
                errors=[],
                warnings=["Translation pipeline is under construction"],
                metadata=self._create_metadata(context, 0, 0, True),
            )

        except Exception as e:
            self.error_handler.handle_exception(
                e, ErrorCategory.TRANSLATION, additional_context="Structured parsing approach"
            )
            logger.error("Structured translation failed: %s", str(e))
            return self._create_failure_result(context, str(e))

    def _create_failure_result(
        self, context: TranslationContext, error_message: str
    ) -> TranslationResult:
        """Create a failure translation result."""
        return TranslationResult(
            success=False,
            code=None,
            errors=[error_message],
            warnings=[],
            metadata=self._create_metadata(context, 0, 0, False),
        )

    def _create_metadata(
        self,
        context: TranslationContext,
        blocks_processed: int,
        blocks_translated: int,
        validation_passed: bool,
    ) -> dict[str, Any]:
        """Create metadata for translation result."""
        duration_ms = int((time.time() - context.start_time) * 1000)

        return {
            "translation_id": context.translation_id,
            "duration_ms": duration_ms,
            "blocks_processed": blocks_processed,
            "blocks_translated": blocks_translated,
            "validation_passed": validation_passed,
            "target_language": context.target_language.value,
            "pipeline_version": "2.0",
        }

    def _emit_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Emit an event through the event system."""
        try:
            # TODO: Implement event bus resolution when EventBus service is created
            logger.debug("Event emitted: %s with data: %s", event_type, data)
        except Exception as e:
            logger.debug("Failed to emit event %s: %s", event_type, e)

    def _initialize_services(self) -> None:
        """Initialize required services in the container."""
        # This method will be expanded as we create the individual services
        # For now, it's a placeholder for service initialization
        logger.debug("Initializing pipeline services")

    def get_statistics(self) -> dict[str, Any]:
        """Get pipeline statistics."""
        return {
            "total_translations": self._translation_counter,
            "error_summary": self.error_handler.get_error_summary(),
        }

    def shutdown(self) -> None:
        """Shutdown the pipeline and clean up resources."""
        try:
            # Shutdown services through container if they support it
            logger.info("Shutting down Translation Pipeline")

            # Clear error statistics
            self.error_handler.clear_error_stats()

            logger.info("Translation Pipeline shutdown complete")
        except Exception as e:
            logger.error("Error during pipeline shutdown: %s", e)

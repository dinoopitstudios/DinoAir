from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .pipeline import StreamingProgress


class StreamingMode(Enum):
    LINE_BY_LINE = "line_by_line"
    BLOCK_BY_BLOCK = "block_by_block"
    FULL_DOCUMENT = "full_document"
    INTERACTIVE = "interactive"


class StreamingEvent(Enum):
    STARTED = "started"
    CHUNK_STARTED = "chunk_started"
    CHUNK_COMPLETED = "chunk_completed"
    TRANSLATION_STARTED = "translation_started"
    TRANSLATION_COMPLETED = "translation_completed"
    PROGRESS_UPDATE = "progress_update"
    ERROR = "error"
    WARNING = "warning"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


@dataclass
class StreamingEventData:
    event: StreamingEvent
    timestamp: float = field(default_factory=time.time)
    chunk_index: int | None = None
    progress: StreamingProgress | None = None
    data: Any | None = None
    error: str | None = None
    warning: str | None = None


@dataclass
class TranslationUpdate:
    chunk_index: int
    block_index: int
    original_content: str
    translated_content: str | None
    is_partial: bool = False
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)


__all__ = [
    "StreamingMode",
    "StreamingEvent",
    "StreamingEventData",
    "TranslationUpdate",
]

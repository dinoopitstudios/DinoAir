from __future__ import annotations

from input_processing import InputPipeline, IntentType, Severity


def _collector():
    messages: list[str] = []
    return messages, lambda m: messages.append(m)


def test_empty_input_returns_unclear():
    messages, feedback = _collector()
    pipeline = InputPipeline(gui_feedback_hook=feedback)
    text, intent = pipeline.run("")
    assert text == ""
    assert intent == IntentType.UNCLEAR
    # optional feedback may or may not be emitted depending on skip_empty_feedback
    assert isinstance(messages, list)


def test_html_like_content_is_escaped_under_claude():
    _, feedback = _collector()
    pipeline = InputPipeline(gui_feedback_hook=feedback, model_type="claude")
    text, _ = pipeline.run("Test < keep ampersand & and escape <tags> like <div>")
    # Ensure angle brackets are escaped as entities for Claude model
    assert "&lt;" in text
    assert "&gt;" in text


def test_escaping_of_raw_angle_brackets_with_claude():
    messages, feedback = _collector()
    pipeline = InputPipeline(gui_feedback_hook=feedback, model_type="claude")
    text, _ = pipeline.run("Test <tag>content</tag>")
    assert "&lt;tag&gt;" in text


def test_custom_profanity_word_is_masked():
    messages, feedback = _collector()
    pipeline = InputPipeline(gui_feedback_hook=feedback)
    pipeline.add_custom_profanity_word("testbadword", Severity.MODERATE)
    text, _ = pipeline.run("This contains testbadword in it")
    assert "testbadword" not in text  # masked or removed


def test_context_clear_roundtrip():
    messages, feedback = _collector()
    pipeline = InputPipeline(gui_feedback_hook=feedback)
    pipeline.run("hello there")
    assert isinstance(pipeline.get_conversation_context(), str)
    assert pipeline.get_conversation_context() != ""
    pipeline.clear_context()
    assert pipeline.get_conversation_context() == ""


def test_rate_limit_stats_shape():
    messages, feedback = _collector()
    pipeline = InputPipeline(gui_feedback_hook=feedback)
    # Single call should pass
    pipeline.run("First request")
    stats = pipeline.get_rate_limit_stats()
    assert isinstance(stats, dict)
    assert "total_requests" in stats
    assert isinstance(stats.get("total_requests"), int)

import pytest
from pseudocode_translator import parser as parser_module
from pseudocode_translator.config import TranslatorConfig
from pseudocode_translator.models import BlockType, CodeBlock
from pseudocode_translator.translator import (
    TranslationManager,
)
from pseudocode_translator.translator import TranslationResult as ManagerTranslationResult
from pseudocode_translator.translator_support.dependency_resolver import DependencyResolver
from pseudocode_translator.translator_support.fix_refiner import attempt_fixes
from pseudocode_translator.translator_support.offload_executor import OffloadExecutor


class FakeValidationResult:
    def __init__(self, errors=None, warnings=None):
        self.errors = errors or []
        self.warnings = warnings or []


def test_dependency_resolver_definitions_and_imports():
    code = """
import os
from math import sqrt

x = 1

def f(a, b):
    return a + b

class C:
    pass
"""
    resolver = DependencyResolver()
    out = resolver.analyze_block(code)
    if "defined_names" not in out:
        raise AssertionError
    if "required_imports" not in out:
        raise AssertionError
    # Top-level function, class and simple assignment present
    if set(out["defined_names"]) < {"f", "C", "x"}:
        raise AssertionError
    # Imports captured in normalized strings
    req = out["required_imports"]
    if not (any(s == "import os" for s in req) or any(s.startswith("from math ") for s in req)):
        raise AssertionError


def test_fix_refiner_attempt_fixes_success_and_exception():
    class ModelOk:
        class _Res:
            def __init__(self, code):
                self.success = True
                self.code = code
                self.errors = []
                self.warnings = []
                self.metadata = {}

        def refine_code(self, code: str, error_context: str, config=None):
            # Return a TranslationResult-like object
            return self._Res(code + "\n# refined")

    class ModelFail:
        def refine_code(self, code: str, error_context: str, config=None):
            raise RuntimeError("refine boom")

    bad_validation = FakeValidationResult(
        errors=["E1: missing colon", "E2: indent",
                "E3: name error", "E4: extra"]
    )
    code = "def x():\n    pass"

    # Success path
    refined, warns = attempt_fixes(ModelOk(), code, bad_validation)
    if not refined.endswith("# refined"):
        raise AssertionError
    assert isinstance(warns, list)

    # Exception path should fall back to original code with no raise
    refined2, warns2 = attempt_fixes(ModelFail(), code, bad_validation)
    if refined2 != code:
        raise AssertionError
    assert isinstance(warns2, list)


def test_offload_executor_gating_and_immediate_fallback(monkeypatch):
    # Minimal exec cfg matching translator semantics
    class ExecCfg:
        process_pool_enabled = True
        process_pool_targets = {"parse", "validate"}
        process_pool_task_timeout_ms = None

    # Fake dispatcher that records events
    class FakeDispatcher:
        def __init__(self):
            self.events = []

        def dispatch_event(self, event_type, payload=None, **kwargs):
            # Record a normalized dict for assertions
            if isinstance(payload, dict):
                self.events.append((str(event_type), dict(payload)))
            else:
                # Some dispatchers may use kwargs; normalize those
                self.events.append(
                    (str(event_type), {**kwargs} if kwargs else {}))

    # Fake pool that returns immediate fallback sentinel
    class FakePool:
        def submit_parse(self, text: str):
            return "exec_pool_fallback:too_large"

        def submit_validate(self, code: str):
            return "exec_pool_fallback:too_large"

    dispatcher = FakeDispatcher()
    recorder = object()  # unused in facade logic for this test
    offload = OffloadExecutor(
        dispatcher=dispatcher,
        recorder=recorder,
        exec_cfg=ExecCfg(),
        ensure_pool_cb=FakePool,
    )

    # Can offload both kinds
    if offload.can_offload("parse") is not True:
        raise AssertionError
    if offload.can_offload("validate") is not True:
        raise AssertionError

    ok_parse, result_parse = offload.submit("parse", "print('x')")
    if ok_parse is not True:
        raise AssertionError
    assert isinstance(result_parse, str)
    if not result_parse.startswith("exec_pool_fallback:"):
        raise AssertionError

    ok_val, result_val = offload.submit("validate", "print('x')")
    if ok_val is not True:
        raise AssertionError
    assert isinstance(result_val, str)
    if not result_val.startswith("exec_pool_fallback:"):
        raise AssertionError

    # When disabled, should not offload
    class ExecCfgDisabled(ExecCfg):
        process_pool_enabled = False

    offload2 = OffloadExecutor(
        dispatcher=dispatcher,
        recorder=recorder,
        exec_cfg=ExecCfgDisabled(),
        ensure_pool_cb=FakePool,
    )
    ok_disabled, result_disabled = offload2.submit("parse", "x")
    if ok_disabled is not False:
        raise AssertionError
    assert result_disabled is None


def test_separate_mixed_block_segmentation(monkeypatch):
    # Patch language scoring to be deterministic for this test:
    # Treat lines starting with "print" as PYTHON, others as ENGLISH
    def fake_score_line_language(line: str) -> float:
        return 1.0 if line.strip().startswith("print") else 0.0

    monkeypatch.setattr(
        parser_module.ParserModule,
        "score_line_language",
        staticmethod(fake_score_line_language),
        raising=True,
    )

    cfg = TranslatorConfig()
    manager = TranslationManager(cfg)

    mixed_text = "Explain how to print OK\nprint('OK')\nAnd say goodbye\nprint('bye')\n"
    line_count = mixed_text.count(
        "\n") + (0 if mixed_text.endswith("\n") else 1)
    block = CodeBlock(
        type=BlockType.MIXED,
        content=mixed_text,
        line_numbers=(1, line_count),
        metadata={"source": "test"},
        context=None,
    )
    parts = manager.separate_mixed_block(block)

    # Expect alternating ENGLISH then PYTHON segments
    assert len(parts) == 4
    if parts[0].type != BlockType.ENGLISH:
        raise AssertionError
    if "Explain" not in parts[0].content:
        raise AssertionError
    if parts[1].type != BlockType.PYTHON:
        raise AssertionError
    if "print('OK')" not in parts[1].content:
        raise AssertionError
    if parts[2].type != BlockType.ENGLISH:
        raise AssertionError
    if "goodbye" not in parts[2].content:
        raise AssertionError
    if parts[3].type != BlockType.PYTHON:
        raise AssertionError
    if "print('bye')" not in parts[3].content:
        raise AssertionError

    # Metadata inheritance flag present
    for p in parts:
        if p.metadata.get("is_sub_block") is not True:
            raise AssertionError


@pytest.mark.parametrize(
    ("llm_first_raises", "structured_ok"),
    [
        (True, True),
        (True, False),
    ],
)
def test_translate_pseudocode_orchestration_guard_clauses(
    monkeypatch, llm_first_raises, structured_ok
):
    cfg = TranslatorConfig()
    manager = TranslationManager(cfg)

    # If internal helpers exist, patch them; else patch the underlying methods they delegate to.
    if hasattr(manager, "_run_llm_first_flow"):

        def _run_llm_first_flow(input_text: str):
            if llm_first_raises:
                return (False, {"warning": "llm error"})
            # Return a manager-level TranslationResult
            return (
                True,
                ManagerTranslationResult(
                    success=True,
                    code="pass",
                    errors=[],
                    warnings=[],
                    metadata={"approach": "llm_first"},
                ),
            )

        monkeypatch.setattr(manager, "_run_llm_first_flow",
                            _run_llm_first_flow, raising=True)
    else:

        def _translate_with_llm_first(self, txt, start_time=None, translation_id=None):
            if llm_first_raises:
                raise RuntimeError("llm boom")
            return ManagerTranslationResult(
                success=True,
                code="pass",
                errors=[],
                warnings=[],
                metadata={"approach": "llm_first"},
            )

        monkeypatch.setattr(
            TranslationManager,
            "_translate_with_llm_first",
            _translate_with_llm_first,
            raising=True,
        )

    if hasattr(manager, "_run_structured_flow"):

        def _run_structured_flow(input_text: str):
            if structured_ok:
                return ManagerTranslationResult(
                    success=True,
                    code="x = 1",
                    errors=[],
                    warnings=[],
                    metadata={"approach": "structured_parsing"},
                )
            return ManagerTranslationResult(
                success=False,
                code="",
                errors=["parse failed"],
                warnings=[],
                metadata={"approach": "structured_parsing"},
            )

        monkeypatch.setattr(manager, "_run_structured_flow",
                            _run_structured_flow, raising=True)
    else:

        def _translate_with_structured_parsing(
            self, txt, start_time=None, translation_id=None, warnings_ref=None
        ):
            if structured_ok:
                return ManagerTranslationResult(
                    success=True,
                    code="x = 1",
                    errors=[],
                    warnings=[],
                    metadata={"approach": "structured_parsing"},
                )
            return ManagerTranslationResult(
                success=False,
                code="",
                errors=["parse failed"],
                warnings=[],
                metadata={"approach": "structured_parsing"},
            )

        monkeypatch.setattr(
            TranslationManager,
            "_translate_with_structured_parsing",
            _translate_with_structured_parsing,
            raising=True,
        )

    res = manager.translate_pseudocode("do something")

    # Validate approach and basic shape
    if not hasattr(res, "code"):
        raise AssertionError
    if "approach" not in getattr(res, "metadata", {}):
        raise AssertionError
    if not llm_first_raises:
        if res.metadata["approach"] != "llm_first":
            raise AssertionError
    else:
        if res.metadata["approach"] != "structured_parsing":
            raise AssertionError

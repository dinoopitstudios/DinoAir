from pseudocode_translator.assembler import CodeAssembler
from pseudocode_translator.config import TranslatorConfig
from pseudocode_translator.models import BlockType, CodeBlock


def test_assemble_minimal_python_blocks_executes():
    cfg = TranslatorConfig()
    assembler = CodeAssembler(cfg)

    blocks = [
        CodeBlock(
            type=BlockType.PYTHON,
            content="import math",
            line_numbers=(1, 1),
            metadata={"has_imports": True},
        ),
        CodeBlock(
            type=BlockType.PYTHON,
            content=("def add(a, b):\n    return a + b\n"),
            line_numbers=(2, 3),
            metadata={"has_functions": True},
        ),
    ]

    code = assembler.assemble(blocks)

    assert isinstance(code, str)
    if "def add(" not in code:
        raise AssertionError

    # Validate it executes and the function works
    env = {}
    exec(code, env, env)  # nosec - controlled test input
    if "add" not in env:
        raise AssertionError
    if not callable(env["add"]):
        raise AssertionError
    if env["add"](2, 3) != 5:
        raise AssertionError

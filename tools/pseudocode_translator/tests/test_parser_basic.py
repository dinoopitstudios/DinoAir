from pseudocode_translator.models import BlockType, CodeBlock, ParseResult
from pseudocode_translator.parser import ParserModule


def test_parse_mixed_blocks():
    parser = ParserModule()
    input_text = (
        "Define a function add(a, b) that returns their sum.\n"
        "It should be a simple pure function.\n"
        "\n"
        "def add(a, b):\n"
        "    return a + b\n"
    )

    blocks = parser.parse(input_text)

    # Basic shape checks
    assert isinstance(blocks, list)
    assert len(blocks) >= 2

    # Type checks and ordering of first two blocks (English then Python)
    assert all(isinstance(b, CodeBlock) for b in blocks)
    first_types = [b.type for b in blocks[:2]]
    assert first_types[0] in (BlockType.ENGLISH, BlockType.MIXED)
    assert BlockType.PYTHON in [b.type for b in blocks]

    # Ensure at least one pure English and one pure Python block exist
    types = [b.type for b in blocks]
    assert BlockType.ENGLISH in types
    assert BlockType.PYTHON in types


def test_get_parse_result_simple_no_errors():
    parser = ParserModule()
    input_text = "Write a simple helper called foo.\n\ndef foo():\n    return 1\n"

    result = parser.get_parse_result(input_text)

    assert isinstance(result, ParseResult)
    # Hermetic check: no fatal errors and blocks were produced
    assert isinstance(result.blocks, list)
    assert len(result.errors) == 0
    assert len(result.blocks) >= 1

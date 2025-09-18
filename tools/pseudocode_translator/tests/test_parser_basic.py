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
    if len(blocks) < 2:
        raise AssertionError

    # Type checks and ordering of first two blocks (English then Python)
    if not all(isinstance(b, CodeBlock) for b in blocks):
        raise AssertionError
    first_types = [b.type for b in blocks[:2]]
    if first_types[0] not in (BlockType.ENGLISH, BlockType.MIXED):
        raise AssertionError
    if BlockType.PYTHON not in [b.type for b in blocks]:
        raise AssertionError

    # Ensure at least one pure English and one pure Python block exist
    types = [b.type for b in blocks]
    if BlockType.ENGLISH not in types:
        raise AssertionError
    if BlockType.PYTHON not in types:
        raise AssertionError


def test_get_parse_result_simple_no_errors():
    parser = ParserModule()
    input_text = "Write a simple helper called foo.\n\ndef foo():\n    return 1\n"

    result = parser.get_parse_result(input_text)

    assert isinstance(result, ParseResult)
    # Hermetic check: no fatal errors and blocks were produced
    assert isinstance(result.blocks, list)
    assert len(result.errors) == 0
    if len(result.blocks) < 1:
        raise AssertionError

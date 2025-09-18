import ast
import textwrap
from types import SimpleNamespace

from tools.pseudocode_translator.validator.logic import LogicValidator


def parse_and_check(src: str) -> list[str]:
    """
    Helper: parse source into AST and run LogicValidator._check_undefined_names
    using a minimal config where check_undefined_vars is enabled.
    """
    tree = ast.parse(textwrap.dedent(src))
    cfg = SimpleNamespace(check_undefined_vars=True)
    validator = LogicValidator(cfg)
    return validator._check_undefined_names(tree)


def assert_contains_issue(messages: list[str], name: str, lineno: int | None = None):
    """
    Assert that at least one message refers to an undefined variable 'name'.
    Optionally assert that a line number appears in some message.
    """
    needle = f"Undefined variable '{name}'"
    assert any(needle in m for m in messages), f"Expected {needle} in {messages}"
    if lineno is not None:
        assert any(f"line {lineno}" in m for m in messages), f"Expected line {lineno} in {messages}"


def test_augassign_requires_prior_definition():
    # AugAssign requires prior definition and does not create a new binding
    src = """def f():
    x += 1
"""
    msgs = parse_and_check(src)
    assert len([m for m in msgs if "Undefined variable 'x'" in m]) == 1
    assert_contains_issue(msgs, "x", lineno=2)


def test_comprehension_target_no_leakage():
    # Comprehension scoping prevents leakage to enclosing/module scope
    src = """[x for x in range(1)]
print(x)
"""
    msgs = parse_and_check(src)
    assert len([m for m in msgs if "Undefined variable 'x'" in m]) == 1
    assert_contains_issue(msgs, "x", lineno=2)


def test_lambda_parameter_scoping():
    # Lambda parameters are scoped correctly
    src = """f = lambda x, y=1: x + y
"""
    msgs = parse_and_check(src)
    assert msgs == []


def test_global_statement_semantics():
    # Global declarations allow reading and writing to module variable
    src = """g = 0
def f():
    global g
    g = g + 1
"""
    msgs = parse_and_check(src)
    assert msgs == []


def test_nonlocal_semantics():
    # Nonlocal declarations resolve against enclosing function scope
    src = """def outer():
    x = 1
    def inner():
        nonlocal x
        x = x + 1
"""
    msgs = parse_and_check(src)
    assert msgs == []


def test_except_as_lifetime():
    # Exception alias is temporary and removed after the except block
    src = """try:
    pass
except Exception as e:
    pass
print(e)
"""
    msgs = parse_and_check(src)
    assert len([m for m in msgs if "Undefined variable 'e'" in m]) == 1
    assert_contains_issue(msgs, "e")


def test_delete_semantics():
    # Deletions create tombstones respected by Scope.is_defined
    src = """a = 1
del a
print(a)
"""
    msgs = parse_and_check(src)
    assert len([m for m in msgs if "Undefined variable 'a'" in m]) == 1
    assert_contains_issue(msgs, "a", lineno=3)


def test_class_body_resolves_against_module_not_enclosing_function_locals():
    # Class body should resolve against module, not enclosing function locals
    src = """def outer():
    x = 1
    class C:
        y = x
"""
    msgs = parse_and_check(src)
    assert len([m for m in msgs if "Undefined variable 'x'" in m]) == 1
    assert_contains_issue(msgs, "x", lineno=4)


def test_star_import_suppression():
    # Star import suppression returns exact single suppression message
    src = """from math import *
print(sin(1))
"""
    msgs = parse_and_check(src)
    assert msgs == ["Star import prevents reliable undefined-name checking"]


def test_async_function_parity():
    # Async constructs parity with sync for undefined checking
    src = """async def foo(x): return x
async def main():
    return await foo(1)
"""
    msgs = parse_and_check(src)
    assert msgs == []


def test_namedexpr_in_if():
    # Walrus binds in the current scope and is usable in the same expression and body
    src = """if (n := 5) > 0:
    x = n
"""
    msgs = parse_and_check(src)
    assert msgs == []


def test_namedexpr_inside_comprehension_no_leak():
    # NamedExpr inside comprehension does not leak to enclosing scope
    src = """xs = [(n := x) for x in range(2)]
print(n)
"""
    msgs = parse_and_check(src)
    assert len([m for m in msgs if "Undefined variable 'n'" in m]) == 1
    assert_contains_issue(msgs, "n", lineno=2)


def test_pattern_matching_case_local_binding():
    # Pattern matching binds are case-local and removed afterward
    src = """obj = {"x": 1}
match obj:
    case {"x": y}:
        print(y)
print(y)
"""
    msgs = parse_and_check(src)
    occurrences = [m for m in msgs if "Undefined variable 'y'" in m]
    assert len(occurrences) == 1

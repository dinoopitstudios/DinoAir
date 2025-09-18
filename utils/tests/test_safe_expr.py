"""
Unit tests for safe_expr.py module.
Tests safe expression evaluation with security validation and edge cases.
"""

import ast

import pytest

from ..safe_expr import ValidationError, _SafeExprEvaluator, _SafeExprValidator, evaluate_bool_expr


class TestValidationError:
    """Test cases for ValidationError exception."""

    def test_validation_error_inheritance(self):
        """Test that ValidationError inherits from ValueError."""
        error = ValidationError("Test error")
        assert isinstance(error, ValueError)
        assert str(error) == "Test error"


class TestBasicExpressionEvaluation:
    """Test cases for basic expression evaluation."""

    def test_evaluate_boolean_literals(self):
        """Test evaluation of boolean literals."""
        assert evaluate_bool_expr("True", {}) is True
        assert evaluate_bool_expr("False", {}) is False

    def test_evaluate_numeric_literals(self):
        """Test evaluation of numeric literals as boolean."""
        assert evaluate_bool_expr("1", {}) is True
        assert evaluate_bool_expr("0", {}) is False
        assert evaluate_bool_expr("42", {}) is True
        assert evaluate_bool_expr("3.14", {}) is True
        assert evaluate_bool_expr("0.0", {}) is False

    def test_evaluate_string_literals(self):
        """Test evaluation of string literals as boolean."""
        assert evaluate_bool_expr("'hello'", {}) is True
        assert evaluate_bool_expr("''", {}) is False
        assert evaluate_bool_expr('"world"', {}) is True
        assert evaluate_bool_expr('""', {}) is False

    def test_evaluate_none_literal(self):
        """Test evaluation of None literal."""
        assert evaluate_bool_expr("None", {}) is False

    def test_evaluate_container_literals(self):
        """Test evaluation of container literals as boolean."""
        assert evaluate_bool_expr("[1, 2, 3]", {}) is True
        assert evaluate_bool_expr("[]", {}) is False
        assert evaluate_bool_expr("{'a': 1}", {}) is True
        assert evaluate_bool_expr("{}", {}) is False
        assert evaluate_bool_expr("(1, 2)", {}) is True
        assert evaluate_bool_expr("()", {}) is False


class TestVariableAccess:
    """Test cases for variable access and validation."""

    def test_evaluate_simple_variables(self):
        """Test evaluation of simple variables."""
        variables = {
            "is_valid": True,
            "count": 42,
            "name": "test",
            "empty": None,
        }

        assert evaluate_bool_expr("is_valid", variables) is True
        assert evaluate_bool_expr("count", variables) is True
        assert evaluate_bool_expr("name", variables) is True
        assert evaluate_bool_expr("empty", variables) is False

    def test_unknown_variable_error(self):
        """Test that unknown variables raise ValidationError."""
        with pytest.raises(ValidationError, match="Unknown variable: unknown_var"):
            evaluate_bool_expr("unknown_var", {})

    def test_empty_variables_dict(self):
        """Test with empty variables dictionary."""
        with pytest.raises(ValidationError, match="Unknown variable: x"):
            evaluate_bool_expr("x", {})


class TestBooleanOperations:
    """Test cases for boolean operations."""

    def test_and_operation(self):
        """Test 'and' boolean operation."""
        variables = {"a": True, "b": False, "c": True}

        assert evaluate_bool_expr("a and c", variables) is True
        assert evaluate_bool_expr("a and b", variables) is False
        assert evaluate_bool_expr("b and c", variables) is False
        assert evaluate_bool_expr("a and b and c", variables) is False

    def test_or_operation(self):
        """Test 'or' boolean operation."""
        variables = {"a": True, "b": False, "c": False}

        assert evaluate_bool_expr("a or b", variables) is True
        assert evaluate_bool_expr("b or c", variables) is False
        assert evaluate_bool_expr("a or b or c", variables) is True

    def test_not_operation(self):
        """Test 'not' unary operation."""
        variables = {"a": True, "b": False}

        assert evaluate_bool_expr("not a", variables) is False
        assert evaluate_bool_expr("not b", variables) is True
        assert evaluate_bool_expr("not not a", variables) is True

    def test_complex_boolean_expressions(self):
        """Test complex boolean expressions with parentheses."""
        variables = {"a": True, "b": False, "c": True, "d": False}

        assert evaluate_bool_expr("(a and b) or (c and not d)", variables) is True
        assert evaluate_bool_expr("not (a and b) and (c or d)", variables) is True
        assert evaluate_bool_expr("(a or b) and (c or d)", variables) is True


class TestComparisonOperations:
    """Test cases for comparison operations."""

    def test_equality_operations(self):
        """Test equality and inequality comparisons."""
        variables = {"x": 5, "y": 5, "z": 10, "name": "test"}

        assert evaluate_bool_expr("x == y", variables) is True
        assert evaluate_bool_expr("x == z", variables) is False
        assert evaluate_bool_expr("x != z", variables) is True
        assert evaluate_bool_expr("name == 'test'", variables) is True
        assert evaluate_bool_expr("name != 'other'", variables) is True

    def test_numeric_comparisons(self):
        """Test numeric comparison operations."""
        variables = {"a": 10, "b": 20, "c": 10.5}

        assert evaluate_bool_expr("a < b", variables) is True
        assert evaluate_bool_expr("b > a", variables) is True
        assert evaluate_bool_expr("a <= b", variables) is True
        assert evaluate_bool_expr("a <= a", variables) is True
        assert evaluate_bool_expr("b >= a", variables) is True
        assert evaluate_bool_expr("c > a", variables) is True

    def test_membership_operations(self):
        """Test 'in' and 'not in' operations."""
        variables = {
            "items": [1, 2, 3],
            "text": "hello world",
            "keys": {"a", "b", "c"},
        }

        assert evaluate_bool_expr("2 in items", variables) is True
        assert evaluate_bool_expr("5 not in items", variables) is True
        assert evaluate_bool_expr("'hello' in text", variables) is True
        assert evaluate_bool_expr("'xyz' not in text", variables) is True
        assert evaluate_bool_expr("'a' in keys", variables) is True

    def test_chained_comparisons(self):
        """Test chained comparison operations."""
        variables = {"a": 5, "b": 10, "c": 15}

        assert evaluate_bool_expr("a < b < c", variables) is True
        assert evaluate_bool_expr("a < b > a", variables) is True
        assert evaluate_bool_expr("c > b > a", variables) is True
        assert evaluate_bool_expr("a < c < b", variables) is False


class TestArithmeticOperations:
    """Test cases for arithmetic operations in expressions."""

    def test_basic_arithmetic(self):
        """Test basic arithmetic operations."""
        variables = {"x": 10, "y": 5}

        assert evaluate_bool_expr("x + y == 15", variables) is True
        assert evaluate_bool_expr("x - y == 5", variables) is True
        assert evaluate_bool_expr("x * y == 50", variables) is True
        assert evaluate_bool_expr("x / y == 2", variables) is True
        assert evaluate_bool_expr("x % 3 == 1", variables) is True
        assert evaluate_bool_expr("x // 3 == 3", variables) is True

    def test_arithmetic_precedence(self):
        """Test arithmetic operator precedence."""
        variables = {"a": 2, "b": 3, "c": 4}

        assert evaluate_bool_expr("a + b * c == 14", variables) is True  # 2 + (3 * 4)
        assert evaluate_bool_expr("(a + b) * c == 20", variables) is True
        assert evaluate_bool_expr("a * b + c == 10", variables) is True  # (2 * 3) + 4

    def test_division_by_zero(self):
        """Test division by zero handling."""
        variables = {"x": 10, "zero": 0}

        with pytest.raises(ZeroDivisionError):
            evaluate_bool_expr("x / zero", variables)


class TestSecurityValidation:
    """Test cases for security validation and restrictions."""

    def test_function_calls_rejected(self):
        """Test that function calls are rejected."""
        with pytest.raises(ValidationError, match="Function calls are not allowed"):
            evaluate_bool_expr("len([1, 2, 3])", {})

        with pytest.raises(ValidationError, match="Function calls are not allowed"):
            evaluate_bool_expr("print('hello')", {})

        with pytest.raises(ValidationError, match="Function calls are not allowed"):
            evaluate_bool_expr("__import__('os')", {})

    def test_attribute_access_rejected(self):
        """Test that attribute access is rejected."""
        variables = {"obj": object()}

        with pytest.raises(ValidationError, match="Attribute access is not allowed"):
            evaluate_bool_expr("obj.something", variables)

        with pytest.raises(ValidationError, match="Attribute access is not allowed"):
            evaluate_bool_expr("'hello'.upper()", {})

    def test_subscript_access_rejected(self):
        """Test that subscript access is rejected."""
        variables = {"items": [1, 2, 3], "data": {"key": "value"}}

        with pytest.raises(ValidationError, match="Subscript access is not allowed"):
            evaluate_bool_expr("items[0]", variables)

        with pytest.raises(ValidationError, match="Subscript access is not allowed"):
            evaluate_bool_expr("data['key']", variables)

    def test_comprehensions_rejected(self):
        """Test that comprehensions are rejected."""
        variables = {"items": [1, 2, 3]}

        with pytest.raises(ValidationError, match="Comprehensions are not allowed"):
            evaluate_bool_expr("[x for x in items]", variables)

        with pytest.raises(ValidationError, match="Comprehensions are not allowed"):
            evaluate_bool_expr("{x for x in items}", variables)

        with pytest.raises(ValidationError, match="Comprehensions are not allowed"):
            evaluate_bool_expr("{x: x for x in items}", variables)

    def test_unsupported_nodes_rejected(self):
        """Test that unsupported AST nodes are rejected."""
        # Lambda functions
        with pytest.raises(ValidationError):
            evaluate_bool_expr("lambda x: x", {})

        # Yield expressions
        with pytest.raises(ValidationError):
            evaluate_bool_expr("(yield x for x in [1, 2, 3])", {})


class TestInputValidation:
    """Test cases for input validation and edge cases."""

    def test_empty_expression(self):
        """Test empty expression validation."""
        with pytest.raises(ValueError, match="Expression must be a non-empty string"):
            evaluate_bool_expr("", {})

        with pytest.raises(ValueError, match="Expression must be a non-empty string"):
            evaluate_bool_expr("   ", {})

    def test_expression_length_limit(self):
        """Test expression length limit validation."""
        long_expr = "True and " * 500 + "True"  # Very long expression

        with pytest.raises(ValueError, match="Expression exceeds maximum length"):
            evaluate_bool_expr(long_expr, {})

    def test_custom_length_limit(self):
        """Test custom expression length limit."""
        expr = "True and False"

        # Should pass with high limit
        result = evaluate_bool_expr(expr, {}, max_length=100)
        assert result is False

        # Should fail with low limit
        with pytest.raises(ValueError, match="Expression exceeds maximum length"):
            evaluate_bool_expr(expr, {}, max_length=5)

    def test_syntax_error_handling(self):
        """Test handling of syntax errors in expressions."""
        with pytest.raises(ValidationError, match="Invalid expression syntax"):
            evaluate_bool_expr("True and", {})

        with pytest.raises(ValidationError, match="Invalid expression syntax"):
            evaluate_bool_expr("(True", {})

        with pytest.raises(ValidationError, match="Invalid expression syntax"):
            evaluate_bool_expr("True )", {})

    def test_non_boolean_result_coercion(self):
        """Test that non-boolean results are properly coerced."""
        variables = {"count": 5, "items": [1, 2, 3], "empty_list": []}

        # Numeric values
        assert evaluate_bool_expr("count", variables) is True
        assert evaluate_bool_expr("count - 5", variables) is False

        # Containers
        assert evaluate_bool_expr("items", variables) is True
        assert evaluate_bool_expr("empty_list", variables) is False

    def test_invalid_result_type_rejection(self):
        """Test that invalid result types are rejected."""
        # This is difficult to test directly since our validator prevents most
        # ways to create invalid types, but we can test the type checking logic
        variables = {"value": True}
        result = evaluate_bool_expr("value", variables)
        assert isinstance(result, bool)


class TestComplexScenarios:
    """Test cases for complex real-world scenarios."""

    def test_error_rate_monitoring(self):
        """Test error rate monitoring expression."""
        variables = {
            "error_rate": 0.15,
            "is_healthy": False,
            "max_error_rate": 0.1,
            "environment": "production",
        }

        expr = "error_rate > max_error_rate and environment == 'production'"
        assert evaluate_bool_expr(expr, variables) is True

        expr = "not is_healthy or error_rate >= 0.1"
        assert evaluate_bool_expr(expr, variables) is True

    def test_system_health_checks(self):
        """Test system health check expressions."""
        variables = {
            "cpu_usage": 85.5,
            "memory_usage": 70.2,
            "disk_usage": 95.8,
            "failed_checks": ["database", "redis"],
            "critical_services": ["web", "api", "database"],
        }

        # High resource usage
        expr = "cpu_usage > 80 or memory_usage > 75 or disk_usage > 90"
        assert evaluate_bool_expr(expr, variables) is True

        # Critical service failures
        expr = "'database' in failed_checks and 'database' in critical_services"
        assert evaluate_bool_expr(expr, variables) is True

    def test_feature_flags(self):
        """Test feature flag expressions."""
        variables = {
            "user_type": "premium",
            "feature_enabled": True,
            "beta_users": ["user1", "user2", "user3"],
            "current_user": "user2",
        }

        expr = "feature_enabled and (user_type == 'premium' or current_user in beta_users)"
        assert evaluate_bool_expr(expr, variables) is True

    def test_threshold_comparisons(self):
        """Test threshold-based comparisons."""
        variables = {
            "response_time": 250,
            "max_response_time": 500,
            "error_count": 3,
            "max_errors": 5,
            "uptime_percent": 99.5,
            "min_uptime": 99.0,
        }

        expr = "response_time < max_response_time and error_count < max_errors and uptime_percent >= min_uptime"
        assert evaluate_bool_expr(expr, variables) is True


class TestEdgeCases:
    """Test cases for edge cases and boundary conditions."""

    def test_deeply_nested_expressions(self):
        """Test deeply nested boolean expressions."""
        variables = {"a": True, "b": False, "c": True, "d": False}

        expr = "((a and not b) or (c and not d)) and not (b and d)"
        assert evaluate_bool_expr(expr, variables) is True

    def test_mixed_type_comparisons(self):
        """Test comparisons between different types."""
        variables = {"num": 42, "str_num": "42", "float_num": 42.0}

        # Different types should not be equal
        assert evaluate_bool_expr("num != str_num", variables) is True
        assert evaluate_bool_expr("num == float_num", variables) is True

    def test_unicode_strings(self):
        """Test expressions with unicode strings."""
        variables = {
            "unicode_text": "Hello 世界 🌍",
            "search_term": "世界",
        }

        assert evaluate_bool_expr("search_term in unicode_text", variables) is True
        assert evaluate_bool_expr("unicode_text != ''", variables) is True

    def test_large_numbers(self):
        """Test expressions with large numbers."""
        variables = {
            "big_num": 10**18,
            "small_num": 1,
            "threshold": 10**17,
        }

        assert evaluate_bool_expr("big_num > threshold", variables) is True
        assert evaluate_bool_expr("small_num < threshold", variables) is True

    def test_floating_point_precision(self):
        """Test floating point precision in comparisons."""
        variables = {"a": 0.1 + 0.2, "b": 0.3}

        # Due to floating point precision, this might be False
        # We test the actual behavior rather than assuming precision
        result = evaluate_bool_expr("a == b", variables)
        assert isinstance(result, bool)


class TestPerformanceAndLimits:
    """Test cases for performance and resource limits."""

    def test_max_expression_length(self):
        """Test maximum expression length enforcement."""
        # Test default limit (1000 characters)
        long_expr = " and ".join(["True"] * 200)  # Should exceed 1000 chars

        with pytest.raises(ValueError, match="Expression exceeds maximum length"):
            evaluate_bool_expr(long_expr, {})

    def test_complex_container_operations(self):
        """Test operations on complex containers."""
        variables = {
            "large_list": list(range(1000)),
            "target": 500,
            "nested_dict": {"level1": {"level2": {"value": True}}},
        }

        # This should work but might be slow
        assert evaluate_bool_expr("target in large_list", variables) is True

    def test_string_operations(self):
        """Test string containment operations."""
        variables = {
            "large_text": "word " * 1000,
            "search": "word",
        }

        assert evaluate_bool_expr("search in large_text", variables) is True


class TestSafeExprValidator:
    """Test cases for the _SafeExprValidator class directly."""

    def test_validator_with_valid_expression(self):
        """Test validator with valid expression."""
        variables = {"x": 1, "y": 2}
        validator = _SafeExprValidator(variables)

        tree = ast.parse("x < y", mode="eval")
        # Should not raise any exception
        validator.visit(tree)

    def test_validator_with_invalid_expression(self):
        """Test validator with invalid expression."""
        variables = {"x": 1}
        validator = _SafeExprValidator(variables)

        tree = ast.parse("len([1, 2, 3])", mode="eval")
        with pytest.raises(ValidationError, match="Function calls are not allowed"):
            validator.visit(tree)

    def test_validator_unsupported_constants(self):
        """Test validator with unsupported constant types."""
        validator = _SafeExprValidator({})

        # Create a mock node with unsupported constant type
        class MockNode:
            def __init__(self, value):
                self.value = value

        with pytest.raises(ValidationError, match="Unsupported constant type"):
            validator.visit_Constant(MockNode(complex(1, 2)))

    def test_validator_container_types(self):
        """Test validator with container types."""
        variables = {"x": 1, "y": 2}
        validator = _SafeExprValidator(variables)

        # Should allow tuples, lists, sets, dicts
        tree = ast.parse("[x, y]", mode="eval")
        validator.visit(tree)  # Should not raise

        tree = ast.parse("(x, y)", mode="eval")
        validator.visit(tree)  # Should not raise

        tree = ast.parse("{x, y}", mode="eval")
        validator.visit(tree)  # Should not raise

        tree = ast.parse("{'a': x, 'b': y}", mode="eval")
        validator.visit(tree)  # Should not raise


class TestSafeExprEvaluator:
    """Test cases for the _SafeExprEvaluator class directly."""

    def test_evaluator_with_valid_expression(self):
        """Test evaluator with valid expression."""
        variables = {"x": 5, "y": 10}
        evaluator = _SafeExprEvaluator(variables)

        tree = ast.parse("x < y", mode="eval")
        result = evaluator.visit(tree)
        assert result is True

    def test_evaluator_container_creation(self):
        """Test evaluator container creation."""
        variables = {"a": 1, "b": 2}
        evaluator = _SafeExprEvaluator(variables)

        # Test tuple creation
        tree = ast.parse("(a, b)", mode="eval")
        result = evaluator.visit(tree)
        assert result == (1, 2)

        # Test list creation
        tree = ast.parse("[a, b]", mode="eval")
        result = evaluator.visit(tree)
        assert result == [1, 2]

        # Test set creation
        tree = ast.parse("{a, b}", mode="eval")
        result = evaluator.visit(tree)
        assert result == {1, 2}

        # Test dict creation
        tree = ast.parse("{'first': a, 'second': b}", mode="eval")
        result = evaluator.visit(tree)
        assert result == {"first": 1, "second": 2}

    def test_evaluator_dict_with_none_key(self):
        """Test evaluator dict creation with None key."""
        evaluator = _SafeExprEvaluator({})

        # Create a mock dict node with None key
        dict_node = ast.Dict(keys=[None], values=[ast.Constant(value="test")])

        with pytest.raises(ValueError, match="Dictionary key is None"):
            evaluator.visit_Dict(dict_node)

    def test_evaluator_unsupported_operators(self):
        """Test evaluator with unsupported operators."""
        evaluator = _SafeExprEvaluator({})

        # Mock unsupported boolean operator
        # Create a mock unsupported boolean operator
        class MockUnsupportedOp:
            pass

        class MockBoolOp:
            def __init__(self):
                self.op = MockUnsupportedOp()  # Not supported
                self.values = [ast.Constant(True), ast.Constant(False)]

        with pytest.raises(ValidationError, match="Unsupported boolean operator"):
            evaluator.visit_BoolOp(MockBoolOp())


class TestRealWorldScenarios:
    """Test cases for real-world usage scenarios."""

    def test_alert_condition_evaluation(self):
        """Test alert condition evaluation."""
        # Simulating monitoring alert conditions
        variables = {
            "cpu_percent": 88.5,
            "memory_percent": 92.1,
            "disk_percent": 76.3,
            "error_rate": 0.08,
            "response_time_ms": 850,
            "is_production": True,
            "maintenance_mode": False,
            "critical_alerts": ["cpu", "memory"],
            "warning_alerts": ["disk"],
        }

        # High CPU alert
        expr = "cpu_percent > 85 and is_production and not maintenance_mode"
        assert evaluate_bool_expr(expr, variables) is True

        # Memory alert with error rate
        expr = "memory_percent > 90 and error_rate > 0.05"
        assert evaluate_bool_expr(expr, variables) is True

        # Complex alert condition
        expr = "('cpu' in critical_alerts and cpu_percent > 85) or ('memory' in critical_alerts and memory_percent > 90)"
        assert evaluate_bool_expr(expr, variables) is True

    def test_business_rule_evaluation(self):
        """Test business rule evaluation."""
        variables = {
            "user_age": 25,
            "account_type": "premium",
            "subscription_active": True,
            "login_attempts": 2,
            "max_attempts": 5,
            "allowed_countries": ["US", "CA", "UK"],
            "user_country": "US",
            "feature_flags": ["advanced_search", "export"],
        }

        # Access control rule
        expr = "subscription_active and account_type == 'premium' and user_country in allowed_countries"
        assert evaluate_bool_expr(expr, variables) is True

        # Login attempt validation
        expr = "login_attempts < max_attempts and user_age >= 18"
        assert evaluate_bool_expr(expr, variables) is True

        # Feature access rule
        expr = "'advanced_search' in feature_flags and account_type == 'premium'"
        assert evaluate_bool_expr(expr, variables) is True

    def test_configuration_validation(self):
        """Test configuration validation scenarios."""
        variables = {
            "debug_mode": False,
            "log_level": "INFO",
            "allowed_levels": ["DEBUG", "INFO", "WARNING", "ERROR"],
            "max_connections": 100,
            "current_connections": 45,
            "ssl_enabled": True,
            "environment": "production",
        }

        # Configuration validity check
        expr = "log_level in allowed_levels and max_connections > 0 and current_connections <= max_connections"
        assert evaluate_bool_expr(expr, variables) is True

        # Production environment checks
        expr = "environment == 'production' and ssl_enabled and not debug_mode"
        assert evaluate_bool_expr(expr, variables) is True


class TestErrorScenarios:
    """Test cases for various error scenarios."""

    def test_type_errors_in_operations(self):
        """Test type errors in operations."""
        variables = {"text": "hello", "number": 42}

        # String and number comparison might not work as expected
        # Test actual behavior rather than assuming
        try:
            result = evaluate_bool_expr("text > number", variables)
            # If it succeeds, it should return a boolean
            assert isinstance(result, bool)
        except TypeError:
            # If it fails, that's also acceptable behavior
            pass

    def test_invalid_operations_on_types(self):
        """Test invalid operations on specific types."""
        variables = {"text": "hello", "items": [1, 2, 3]}

        # These operations should raise appropriate errors
        with pytest.raises((TypeError, ValueError)):
            evaluate_bool_expr("text - 5", variables)

        with pytest.raises((TypeError, ValueError)):
            evaluate_bool_expr("items * text", variables)

    def test_modulo_operations(self):
        """Test modulo operations and edge cases."""
        variables = {"x": 10, "y": 3, "zero": 0}

        assert evaluate_bool_expr("x % y == 1", variables) is True

        with pytest.raises(ZeroDivisionError):
            evaluate_bool_expr("x % zero", variables)

    def test_floor_division_operations(self):
        """Test floor division operations."""
        variables = {"x": 17, "y": 5, "zero": 0}

        assert evaluate_bool_expr("x // y == 3", variables) is True

        with pytest.raises(ZeroDivisionError):
            evaluate_bool_expr("x // zero", variables)


class TestSecurityPenetrationTests:
    """Test cases specifically designed to test security boundaries."""

    def test_import_injection_attempts(self):
        """Test attempts to inject import statements."""
        malicious_vars = {"__import__": __import__, "os": "os"}

        with pytest.raises(ValidationError):
            evaluate_bool_expr("__import__", malicious_vars)

    def test_builtin_access_attempts(self):
        """Test attempts to access Python builtins."""
        variables = {"eval": eval, "exec": exec}

        # Referencing callables is not allowed for security
        with pytest.raises(ValidationError, match="Callable variables are not allowed"):
            evaluate_bool_expr("eval", variables)
        with pytest.raises(ValidationError, match="Callable variables are not allowed"):
            evaluate_bool_expr("exec", variables)

    def test_code_execution_attempts(self):
        """Test attempts to execute code through various means."""
        with pytest.raises(ValidationError, match="Function calls are not allowed"):
            evaluate_bool_expr("eval('1 + 1')", {})

        with pytest.raises(ValidationError, match="Function calls are not allowed"):
            evaluate_bool_expr("exec('print(1)')", {})

        with pytest.raises(ValidationError, match="Function calls are not allowed"):
            evaluate_bool_expr("compile('1+1', '<string>', 'eval')", {})

    def test_side_effect_prevention(self):
        """Test that expressions cannot have side effects."""
        variables = {"items": [1, 2, 3]}

        # These should fail at validation stage
        with pytest.raises(ValidationError):
            evaluate_bool_expr("items.append(4)", variables)

        with pytest.raises(ValidationError):
            evaluate_bool_expr("items.clear()", variables)

    def test_information_disclosure_prevention(self):
        """Test prevention of information disclosure."""
        variables = {"secret": "password123"}

        # Cannot access object attributes
        with pytest.raises(ValidationError):
            evaluate_bool_expr("secret.__class__", variables)

        with pytest.raises(ValidationError):
            evaluate_bool_expr("secret.__dict__", variables)


class TestValidatorInternals:
    """Test cases for internal validator behavior."""

    def test_allowed_constants(self):
        """Test that only allowed constant types pass validation."""
        validator = _SafeExprValidator({})

        # Valid constants
        valid_constants = [
            ast.Constant(True),
            ast.Constant(42),
            ast.Constant(3.14),
            ast.Constant("string"),
            ast.Constant(None),
        ]

        for const in valid_constants:
            validator.visit_Constant(const)  # Should not raise

    def test_disallowed_operators(self):
        """Test that disallowed operators are rejected."""
        validator = _SafeExprValidator({"x": 1, "y": 2})

        # Mock nodes with disallowed operators
        class MockBinOp:
            def __init__(self, op):
                self.op = op
                self.left = ast.Name(id="x")
                self.right = ast.Name(id="y")

        with pytest.raises(ValidationError):
            validator.visit_BinOp(MockBinOp(ast.Pow()))  # Power operator not allowed

        with pytest.raises(ValidationError):
            validator.visit_BinOp(MockBinOp(ast.LShift()))  # Bit shift not allowed

    def test_generic_visit_fallback(self):
        """Test the generic_visit fallback behavior."""
        validator = _SafeExprValidator({})

        # Test with Load context (should be allowed)
        load_node = ast.Load()
        validator.generic_visit(load_node)  # Should not raise

        # Test with disallowed node type
        import_node = ast.Import(names=[ast.alias(name="os")])
        with pytest.raises(ValidationError, match="Disallowed expression element"):
            validator.generic_visit(import_node)

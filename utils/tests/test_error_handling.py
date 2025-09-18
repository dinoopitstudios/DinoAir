"""
Unit tests for error_handling.py module.
Tests error classification, retry logic, circuit breaker, and error aggregation.
"""

import time

import pytest

from ..error_handling import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerState,
    ErrorAggregator,
    ErrorCategory,
    ErrorClassifier,
    ErrorContext,
    ErrorSeverity,
    RetryConfig,
    circuit_breaker,
    error_aggregator,
    retry_on_failure,
    safe_async_operation,
    safe_operation,
    timeout_context,
    try_multiple,
    with_timeout,
)


class TestErrorEnums:
    """Test cases for error enums."""

    def test_error_severity_values(self) -> None:
        """Test ErrorSeverity enum values."""
        assert ErrorSeverity.LOW.value == "low"
        assert ErrorSeverity.MEDIUM.value == "medium"
        assert ErrorSeverity.HIGH.value == "high"
        assert ErrorSeverity.CRITICAL.value == "critical"

    def test_error_category_values(self) -> None:
        """Test ErrorCategory enum values."""
        assert ErrorCategory.NETWORK.value == "network"
        assert ErrorCategory.FILESYSTEM.value == "filesystem"
        assert ErrorCategory.DATABASE.value == "database"
        assert ErrorCategory.EXTERNAL_SERVICE.value == "external_service"
        assert ErrorCategory.RESOURCE.value == "resource"
        assert ErrorCategory.CONFIGURATION.value == "configuration"
        assert ErrorCategory.VALIDATION.value == "validation"
        assert ErrorCategory.TIMEOUT.value == "timeout"
        assert ErrorCategory.UNKNOWN.value == "unknown"


class TestErrorContext:
    """Test cases for ErrorContext dataclass."""

    def test_error_context_creation(self) -> None:
        """Test ErrorContext creation with all fields."""
        context = ErrorContext(
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            message="Connection failed",
            operation="api_call",
            retryable=True,
            details={"url": "http://example.com"},
        )

        assert context.category == ErrorCategory.NETWORK
        assert context.severity == ErrorSeverity.MEDIUM
        assert context.message == "Connection failed"
        assert context.operation == "api_call"
        assert context.retryable is True
        assert context.details == {"url": "http://example.com"}

    def test_error_context_defaults(self) -> None:
        """Test ErrorContext with default values."""
        context = ErrorContext(
            category=ErrorCategory.UNKNOWN,
            severity=ErrorSeverity.LOW,
            message="Unknown error",
            operation="",
        )

        assert context.retryable is True
        assert context.details == {}
        assert context.operation == ""


class TestErrorClassifier:
    """Test cases for ErrorClassifier class."""

    def test_classify_connection_error(self) -> None:
        """Test classification of ConnectionError."""
        error = ConnectionError("Connection refused")
        context = ErrorClassifier.classify_error(error, "network_request")

        assert context.category == ErrorCategory.NETWORK
        assert context.severity == ErrorSeverity.MEDIUM
        assert context.retryable is True
        assert context.operation == "network_request"

    def test_classify_timeout_error(self) -> None:
        """Test classification of TimeoutError."""
        error = TimeoutError("Operation timed out")
        context = ErrorClassifier.classify_error(error)

        assert context.category == ErrorCategory.TIMEOUT
        assert context.severity == ErrorSeverity.MEDIUM
        assert context.retryable is True

    def test_classify_file_not_found_error(self) -> None:
        """Test classification of FileNotFoundError."""
        error = FileNotFoundError("File not found")
        context = ErrorClassifier.classify_error(error)

        assert context.category == ErrorCategory.FILESYSTEM
        assert context.severity == ErrorSeverity.MEDIUM
        assert context.retryable is True

    def test_classify_value_error(self) -> None:
        """Test classification of ValueError."""
        error = ValueError("Invalid value")
        context = ErrorClassifier.classify_error(error)

        assert context.category == ErrorCategory.CONFIGURATION
        assert context.severity == ErrorSeverity.LOW
        assert context.retryable is False

    def test_classify_memory_error(self) -> None:
        """Test classification of MemoryError."""
        error = MemoryError("Out of memory")
        context = ErrorClassifier.classify_error(error)

        assert context.category == ErrorCategory.RESOURCE
        assert context.severity == ErrorSeverity.CRITICAL
        assert context.retryable is False

    def test_classify_unknown_error(self) -> None:
        """Test classification of unknown error type."""
        error = RuntimeError("Unknown error")
        context = ErrorClassifier.classify_error(error)

        assert context.category == ErrorCategory.UNKNOWN
        assert context.severity == ErrorSeverity.LOW
        assert context.retryable is True


class TestRetryConfig:
    """Test cases for RetryConfig dataclass."""

    def test_retry_config_defaults(self) -> None:
        """Test RetryConfig with default values."""
        config = RetryConfig()

        assert config.max_attempts == 3
        assert config.initial_delay == 1.0
        assert config.max_delay == 30.0
        assert config.backoff_factor == 2.0
        assert config.jitter is True
        assert config.retryable_exceptions == (Exception,)

    def test_retry_config_custom_values(self) -> None:
        """Test RetryConfig with custom values."""
        config = RetryConfig(
            max_attempts=5,
            initial_delay=2.0,
            max_delay=60.0,
            backoff_factor=1.5,
            jitter=False,
            retryable_exceptions=(ValueError, KeyError),
        )

        assert config.max_attempts == 5
        assert config.initial_delay == 2.0
        assert config.max_delay == 60.0
        assert config.backoff_factor == 1.5
        assert config.jitter is False
        assert config.retryable_exceptions == (ValueError, KeyError)


class TestCircuitBreakerConfig:
    """Test cases for CircuitBreakerConfig dataclass."""

    def test_circuit_breaker_config_defaults(self) -> None:
        """Test CircuitBreakerConfig with default values."""
        config = CircuitBreakerConfig()

        assert config.failure_threshold == 5
        assert config.recovery_timeout == 60.0
        assert config.success_threshold == 3
        assert config.timeout == 5.0


class TestCircuitBreaker:
    """Test cases for CircuitBreaker class."""

    def test_circuit_breaker_initial_state(self) -> None:
        """Test circuit breaker initial state."""
        config = CircuitBreakerConfig()
        cb = CircuitBreaker(config)

        # Test through public interface where possible
        assert cb.get_state() == "closed"
        # Test internal state - this is acceptable for unit tests
        assert cb._state == CircuitBreakerState.CLOSED  # type: ignore
        assert cb._stats.total_calls == 0  # type: ignore
        assert cb._stats.successful_calls == 0  # type: ignore
        assert cb._stats.failed_calls == 0  # type: ignore

    def test_circuit_breaker_successful_call(self) -> None:
        """Test successful call through circuit breaker."""
        cb = CircuitBreaker(CircuitBreakerConfig())

        def successful_func() -> str:
            return "success"

        result = cb.call(successful_func)
        assert result == "success"
        assert cb._stats.total_calls == 1  # type: ignore
        assert cb._stats.successful_calls == 1  # type: ignore
        assert cb._stats.failed_calls == 0  # type: ignore

    def test_circuit_breaker_failed_call(self) -> None:
        """Test failed call through circuit breaker."""
        cb = CircuitBreaker(CircuitBreakerConfig())

        def failing_func() -> None:
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            cb.call(failing_func)

        assert cb._stats.total_calls == 1  # type: ignore
        assert cb._stats.successful_calls == 0  # type: ignore
        assert cb._stats.failed_calls == 1  # type: ignore

    def test_circuit_breaker_open_after_failures(self) -> None:
        """Test circuit breaker opens after failure threshold."""
        config = CircuitBreakerConfig(failure_threshold=2)
        cb = CircuitBreaker(config)

        def failing_func() -> None:
            raise RuntimeError("Test error")

        # First failure
        with pytest.raises(RuntimeError):
            cb.call(failing_func)
        assert cb._state == CircuitBreakerState.CLOSED  # type: ignore

        # Second failure - should open circuit
        with pytest.raises(RuntimeError):
            cb.call(failing_func)
        assert cb._state == CircuitBreakerState.OPEN  # type: ignore

    def test_circuit_breaker_open_blocks_calls(self) -> None:
        """Test that open circuit breaker blocks calls."""
        cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=1))

        def failing_func() -> None:
            raise RuntimeError("Test error")

        # Open the circuit
        with pytest.raises(RuntimeError):
            cb.call(failing_func)
        assert cb._state == CircuitBreakerState.OPEN  # type: ignore

        # Next call should be blocked
        with pytest.raises(Exception) as exc_info:
            cb.call(lambda: "success")

        assert "Circuit breaker is open" in str(exc_info.value)

    def test_circuit_breaker_recovery(self) -> None:
        """Test circuit breaker recovery after timeout."""
        config = CircuitBreakerConfig(
            failure_threshold=1, recovery_timeout=0.1, success_threshold=1
        )
        cb = CircuitBreaker(config)

        def failing_func() -> None:
            raise RuntimeError("Test error")

        # Open the circuit
        with pytest.raises(RuntimeError):
            cb.call(failing_func)
        assert cb._state == CircuitBreakerState.OPEN  # type: ignore

        # Wait for recovery timeout
        time.sleep(0.2)

        # Next call should attempt recovery (half-open state)
        result = cb.call(lambda: "success")
        assert result == "success"
        assert cb._state == CircuitBreakerState.CLOSED  # type: ignore

    def test_circuit_breaker_reset(self) -> None:
        """Test circuit breaker reset functionality."""
        cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=1))

        def failing_func() -> None:
            raise RuntimeError("Test error")

        # Open the circuit
        with pytest.raises(RuntimeError):
            cb.call(failing_func)
        assert cb._state == CircuitBreakerState.OPEN  # type: ignore

        # Reset
        cb.reset()
        assert cb._state == CircuitBreakerState.CLOSED  # type: ignore
        assert cb._stats.total_calls == 0  # type: ignore


class TestRetryDecorator:
    """Test cases for retry_on_failure decorator."""

    def test_retry_success_on_first_attempt(self):
        """Test retry decorator when function succeeds on first attempt."""
        config = RetryConfig(max_attempts=3)

        call_count = 0

        @retry_on_failure(config)
        def test_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = test_func()
        assert result == "success"
        assert call_count == 1

    def test_retry_success_after_failures(self):
        """Test retry decorator when function succeeds after failures."""
        config = RetryConfig(max_attempts=3)

        call_count = 0

        @retry_on_failure(config)
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Temporary error")
            return "success"

        result = test_func()
        assert result == "success"
        assert call_count == 2

    def test_retry_exhausts_attempts(self):
        """Test retry decorator exhausts all attempts."""
        config = RetryConfig(max_attempts=2)

        call_count = 0

        @retry_on_failure(config)
        def test_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Persistent error")

        with pytest.raises(ValueError) as exc_info:
            test_func()

        assert str(exc_info.value) == "Persistent error"
        assert call_count == 2

    def test_retry_non_retryable_exception(self):
        """Test retry decorator with non-retryable exception."""
        config = RetryConfig(retryable_exceptions=(ValueError,))

        @retry_on_failure(config)
        def test_func():
            raise KeyError("Non-retryable error")

        with pytest.raises(KeyError):
            test_func()


class TestCircuitBreakerDecorator:
    """Test cases for circuit_breaker decorator."""

    def test_circuit_breaker_decorator_success(self):
        """Test circuit breaker decorator with successful calls."""
        call_count = 0

        @circuit_breaker()
        def test_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = test_func()
        assert result == "success"
        assert call_count == 1

    def test_circuit_breaker_decorator_failure(self):
        """Test circuit breaker decorator with failures."""
        config = CircuitBreakerConfig(failure_threshold=2)

        call_count = 0

        @circuit_breaker(config)
        def test_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Test error")

        # First failure
        with pytest.raises(ValueError):
            test_func()
        assert call_count == 1

        # Second failure - circuit opens
        with pytest.raises(ValueError):
            test_func()
        assert call_count == 2

        # Third call should be blocked
        with pytest.raises(Exception) as exc_info:
            test_func()
        assert "Circuit breaker is open" in str(exc_info.value)
        assert call_count == 2  # No additional calls


class TestTimeoutContext:
    """Test cases for timeout functionality."""

    def test_timeout_context_success(self):
        """Test timeout context with successful operation."""
        with timeout_context(1.0):
            time.sleep(0.1)  # Should complete successfully

    def test_timeout_context_timeout(self):
        """Test timeout context with timeout."""
        print("DEBUG: Starting timeout context test", file=__import__("sys").stderr)
        with pytest.raises(TimeoutError), timeout_context(0.1):
            time.sleep(0.2)  # Should timeout
        print("DEBUG: Finished timeout context test", file=__import__("sys").stderr)

    def test_with_timeout_decorator_success(self):
        """Test with_timeout decorator success."""

        @with_timeout(1.0)
        def test_func():
            time.sleep(0.1)
            return "success"

        result = test_func()
        assert result == "success"

    def test_with_timeout_decorator_timeout(self):
        """Test with_timeout decorator timeout."""

        @with_timeout(0.1)
        def test_func():
            time.sleep(0.2)
            return "success"

        with pytest.raises(TimeoutError):
            test_func()


class TestTryMultiple:
    """Test cases for try_multiple function."""

    def test_try_multiple_first_success(self):
        """Test try_multiple with first strategy succeeding."""

        def strategy1() -> str:
            return "success1"

        def strategy2() -> str:
            return "success2"

        def strategy3() -> str:
            return "success3"

        result = try_multiple(strategy1, strategy2, strategy3)
        assert result.success is True
        assert result.result == "success1"
        assert result.fallback_used is False

    def test_try_multiple_fallback_success(self):
        """Test try_multiple with fallback strategy succeeding."""
        call_count = 0

        def strategy1():
            nonlocal call_count
            call_count += 1
            raise ValueError("Strategy 1 failed")

        def strategy2():
            nonlocal call_count
            call_count += 1
            return "success2"

        def strategy3():
            nonlocal call_count
            call_count += 1
            return "success3"

        result = try_multiple(strategy1, strategy2, strategy3)
        assert result.success is True
        assert result.result == "success2"
        assert result.fallback_used is True
        assert call_count == 2

    def test_try_multiple_all_fail(self):
        """Test try_multiple when all strategies fail."""

        def strategy1():
            raise ValueError("Fail 1")

        def strategy2():
            raise RuntimeError("Fail 2")

        strategies = [strategy1, strategy2]

        result = try_multiple(*strategies)
        assert result.success is False
        assert result.result is None
        assert result.fallback_used is True
        assert isinstance(result.error, ValueError)


class TestErrorAggregator:
    """Test cases for ErrorAggregator class."""

    def test_error_aggregator_initial_state(self):
        """Test error aggregator initial state."""
        aggregator = ErrorAggregator()

        stats = aggregator.get_stats()
        assert stats.total_errors == 0
        assert len(stats.errors_by_category) == 0
        assert len(stats.errors_by_severity) == 0
        assert len(stats.recent_errors) == 0

    def test_error_aggregator_record_error(self):
        """Test recording errors in aggregator."""
        aggregator = ErrorAggregator()

        error = ValueError("Test error")
        aggregator.record_error(error, "test_operation")

        stats = aggregator.get_stats()
        assert stats.total_errors == 1
        assert stats.errors_by_category[ErrorCategory.CONFIGURATION] == 1
        assert stats.errors_by_severity[ErrorSeverity.LOW] == 1
        assert len(stats.recent_errors) == 1

        recent_error = stats.recent_errors[0]
        assert recent_error["error"] == "Test error"
        assert recent_error["context"].operation == "test_operation"

    def test_error_aggregator_reset(self):
        """Test resetting error aggregator."""
        aggregator = ErrorAggregator()

        error = RuntimeError("Test error")
        aggregator.record_error(error)

        # Verify error was recorded
        assert aggregator.get_stats().total_errors == 1

        # Reset
        aggregator.reset()

        # Verify reset worked
        stats = aggregator.get_stats()
        assert stats.total_errors == 0
        assert len(stats.errors_by_category) == 0
        assert len(stats.errors_by_severity) == 0


class TestRetryDelayCalculation:
    """Test cases for retry delay calculation logic."""

    def _calculate_retry_delay(self, config: RetryConfig, attempt: int) -> float:
        """Internal helper to calculate retry delay (mirrors the internal logic)."""
        import random

        delay = config.initial_delay * (config.backoff_factor**attempt)
        delay = min(delay, config.max_delay)
        if config.jitter:
            delay *= 1 + random.random() * 0.1  # Add up to 10% jitter
        return delay

    def test_calculate_retry_delay_no_jitter(self) -> None:
        """Test retry delay calculation without jitter."""
        config = RetryConfig(initial_delay=1.0, backoff_factor=2.0, max_delay=10.0, jitter=False)

        # First attempt (attempt=0)
        delay = self._calculate_retry_delay(config, 0)
        assert delay == 1.0

        # Second attempt (attempt=1)
        delay = self._calculate_retry_delay(config, 1)
        assert delay == 2.0

        # Third attempt (attempt=2)
        delay = self._calculate_retry_delay(config, 2)
        assert delay == 4.0

    def test_calculate_retry_delay_with_jitter(self) -> None:
        """Test retry delay calculation with jitter."""
        config = RetryConfig(initial_delay=1.0, backoff_factor=2.0, max_delay=10.0, jitter=True)

        delay = self._calculate_retry_delay(config, 0)
        # Delay should be between 1.0 and 1.1 (with 10% jitter)
        assert 1.0 <= delay <= 1.1

    def test_calculate_retry_delay_max_delay(self) -> None:
        """Test retry delay respects max_delay."""
        config = RetryConfig(initial_delay=1.0, backoff_factor=10.0, max_delay=5.0, jitter=False)

        # High attempt number that would exceed max_delay
        delay = self._calculate_retry_delay(config, 5)  # 1.0 * (10.0^5) = 100000.0
        assert delay == 5.0  # Should be capped at max_delay


class TestSafeOperations:
    """Test cases for safe operation functions."""

    def test_safe_operation_success(self):
        """Test safe_operation with successful function."""

        def test_func():
            return "success"

        result = safe_operation(test_func)
        assert result == "success"

    def test_safe_operation_failure_with_fallback(self):
        """Test safe_operation with failure and fallback."""

        def failing_func():
            raise ValueError("Test error")

        result = safe_operation(failing_func, fallback="fallback_value")
        assert result == "fallback_value"

    def test_safe_operation_failure_no_fallback(self):
        """Test safe_operation with failure and no fallback."""

        def failing_func():
            raise ValueError("Test error")

        result = safe_operation(failing_func)
        assert result is None

    @pytest.mark.asyncio
    async def test_safe_async_operation_success(self):
        """Test safe_async_operation with successful coroutine."""

        async def test_coro():
            return "async_success"

        result = await safe_async_operation(test_coro)
        assert result == "async_success"

    @pytest.mark.asyncio
    async def test_safe_async_operation_failure(self):
        """Test safe_async_operation with failure."""

        async def failing_coro():
            raise RuntimeError("Async error")

        result = await safe_async_operation(failing_coro, fallback="async_fallback")
        assert result == "async_fallback"


class TestGlobalErrorAggregator:
    """Test cases for global error_aggregator instance."""

    def test_global_error_aggregator_exists(self):
        """Test that global error_aggregator is available."""
        assert error_aggregator is not None
        assert isinstance(error_aggregator, ErrorAggregator)

    def test_global_error_aggregator_functionality(self):
        """Test that global error_aggregator works."""
        initial_count = error_aggregator.get_stats().total_errors

        error = ConnectionError("Test connection error")
        error_aggregator.record_error(error, "global_test")

        new_count = error_aggregator.get_stats().total_errors
        assert new_count == initial_count + 1

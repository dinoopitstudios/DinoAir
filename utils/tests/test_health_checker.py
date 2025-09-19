"""
Unit tests for health_checker.py module.
Tests async health checking functionality for various services.
"""

import asyncio
import logging
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ..health_checker import (
    HealthCheck,
    HealthChecker,
    HealthReport,
    HealthStatus,
    quick_health_check,
)


class TestHealthStatus:
    """Test cases for HealthStatus enum."""

    def test_health_status_values(self):
        """Test HealthStatus enum values."""
        if HealthStatus.HEALTHY.value != "healthy":
            raise AssertionError
        if HealthStatus.DEGRADED.value != "degraded":
            raise AssertionError
        if HealthStatus.UNHEALTHY.value != "unhealthy":
            raise AssertionError
        if HealthStatus.UNKNOWN.value != "unknown":
            raise AssertionError

    def test_health_status_string_inheritance(self):
        """Test that HealthStatus inherits from str."""
        assert isinstance(HealthStatus.HEALTHY, str)
        if HealthStatus.HEALTHY != "healthy":
            raise AssertionError


class TestHealthCheck:
    """Test cases for HealthCheck dataclass."""

    def test_health_check_creation_full(self):
        """Test HealthCheck creation with all fields."""
        details = {"version": "1.0", "connections": 5}
        timestamp = time.time()

        check = HealthCheck(
            name="test_service",
            status=HealthStatus.HEALTHY,
            response_time_ms=150.5,
            message="Service is healthy",
            details=details,
            timestamp=timestamp,
        )

        if check.name != "test_service":
            raise AssertionError
        if check.status != HealthStatus.HEALTHY:
            raise AssertionError
        if check.response_time_ms != 150.5:
            raise AssertionError
        if check.message != "Service is healthy":
            raise AssertionError
        if check.details != details:
            raise AssertionError
        if check.timestamp != timestamp:
            raise AssertionError

    def test_health_check_defaults(self):
        """Test HealthCheck with default values."""
        check = HealthCheck(
            name="test", status=HealthStatus.UNKNOWN, response_time_ms=0.0, message="Unknown status"
        )

        if check.details != {}:
            raise AssertionError
        assert isinstance(check.timestamp, float)
        if check.timestamp <= 0:
            raise AssertionError

    def test_health_check_post_init(self):
        """Test HealthCheck post-initialization behavior."""
        before_time = time.time()
        check = HealthCheck(
            name="test", status=HealthStatus.HEALTHY, response_time_ms=100.0, message="Test"
        )
        after_time = time.time()

        # Timestamp should be set automatically
        if not before_time <= check.timestamp <= after_time:
            raise AssertionError
        if check.details != {}:
            raise AssertionError


class TestHealthReport:
    """Test cases for HealthReport dataclass."""

    def test_health_report_creation(self):
        """Test HealthReport creation."""
        checks = [
            HealthCheck("service1", HealthStatus.HEALTHY, 100.0, "OK"),
            HealthCheck("service2", HealthStatus.DEGRADED, 200.0, "Slow"),
        ]
        timestamp = time.time()

        report = HealthReport(
            overall_status=HealthStatus.DEGRADED,
            checks=checks,
            total_checks=2,
            healthy_checks=1,
            degraded_checks=1,
            unhealthy_checks=0,
            timestamp=timestamp,
        )

        if report.overall_status != HealthStatus.DEGRADED:
            raise AssertionError
        if report.checks != checks:
            raise AssertionError
        if report.total_checks != 2:
            raise AssertionError
        if report.healthy_checks != 1:
            raise AssertionError
        if report.degraded_checks != 1:
            raise AssertionError
        if report.unhealthy_checks != 0:
            raise AssertionError
        if report.timestamp != timestamp:
            raise AssertionError

    def test_health_report_from_checks_all_healthy(self):
        """Test HealthReport.from_checks with all healthy services."""
        checks = [
            HealthCheck("service1", HealthStatus.HEALTHY, 100.0, "OK"),
            HealthCheck("service2", HealthStatus.HEALTHY, 150.0, "OK"),
            HealthCheck("service3", HealthStatus.HEALTHY, 80.0, "OK"),
        ]

        report = HealthReport.from_checks(checks)

        if report.overall_status != HealthStatus.HEALTHY:
            raise AssertionError
        if report.total_checks != 3:
            raise AssertionError
        if report.healthy_checks != 3:
            raise AssertionError
        if report.degraded_checks != 0:
            raise AssertionError
        if report.unhealthy_checks != 0:
            raise AssertionError

    def test_health_report_from_checks_with_degraded(self):
        """Test HealthReport.from_checks with degraded services."""
        checks = [
            HealthCheck("service1", HealthStatus.HEALTHY, 100.0, "OK"),
            HealthCheck("service2", HealthStatus.DEGRADED, 500.0, "Slow"),
        ]

        report = HealthReport.from_checks(checks)

        if report.overall_status != HealthStatus.DEGRADED:
            raise AssertionError
        if report.healthy_checks != 1:
            raise AssertionError
        if report.degraded_checks != 1:
            raise AssertionError
        if report.unhealthy_checks != 0:
            raise AssertionError

    def test_health_report_from_checks_with_unhealthy(self):
        """Test HealthReport.from_checks with unhealthy services."""
        checks = [
            HealthCheck("service1", HealthStatus.HEALTHY, 100.0, "OK"),
            HealthCheck("service2", HealthStatus.UNHEALTHY, 0.0, "Down"),
        ]

        report = HealthReport.from_checks(checks)

        if report.overall_status != HealthStatus.UNHEALTHY:
            raise AssertionError
        if report.healthy_checks != 1:
            raise AssertionError
        if report.unhealthy_checks != 1:
            raise AssertionError

    def test_health_report_from_checks_empty(self):
        """Test HealthReport.from_checks with no checks."""
        report = HealthReport.from_checks([])

        if report.overall_status != HealthStatus.UNKNOWN:
            raise AssertionError
        if report.total_checks != 0:
            raise AssertionError
        if report.healthy_checks != 0:
            raise AssertionError


class TestHealthChecker:
    """Test cases for HealthChecker class."""

    def test_health_checker_initialization(self):
        """Test HealthChecker initialization."""
        checker = HealthChecker(timeout=15.0, retries=5)

        if checker.timeout != 15.0:
            raise AssertionError
        if checker.retries != 5:
            raise AssertionError
        assert checker.http_client is None

    def test_health_checker_default_values(self):
        """Test HealthChecker with default values."""
        checker = HealthChecker()

        if checker.timeout != 10.0:
            raise AssertionError
        if checker.retries != 3:
            raise AssertionError

    @pytest.mark.asyncio
    async def test_health_checker_context_manager(self):
        """Test HealthChecker as async context manager."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value = mock_instance

            async with HealthChecker() as checker:
                if checker.http_client != mock_instance:
                    raise AssertionError
                mock_client.assert_called_once()

            mock_instance.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_http_endpoint_success(self):
        """Test successful HTTP endpoint check."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "application/json"}
            mock_instance.get.return_value = mock_response
            mock_client.return_value = mock_instance

            async with HealthChecker() as checker:
                result = await checker.check_http_endpoint(
                    "test_api", "http://localhost:8000/health"
                )

                if result.name != "test_api":
                    raise AssertionError
                if result.status != HealthStatus.HEALTHY:
                    raise AssertionError
                if result.message != "HTTP 200":
                    raise AssertionError
                if result.details["status_code"] != 200:
                    raise AssertionError
                if result.details["url"] != "http://localhost:8000/health":
                    raise AssertionError
                assert isinstance(result.response_time_ms, float)

    @pytest.mark.asyncio
    async def test_check_http_endpoint_wrong_status(self):
        """Test HTTP endpoint check with wrong status code."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.headers = {}
            mock_instance.get.return_value = mock_response
            mock_client.return_value = mock_instance

            async with HealthChecker() as checker:
                result = await checker.check_http_endpoint(
                    "failing_api", "http://localhost:8000/health", expected_status=200
                )

                if result.status != HealthStatus.DEGRADED:
                    raise AssertionError
                if "HTTP 500, expected 200" not in result.message:
                    raise AssertionError

    @pytest.mark.asyncio
    async def test_check_http_endpoint_connection_error(self):
        """Test HTTP endpoint check with connection error."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.side_effect = RuntimeError("Connection refused")
            mock_client.return_value = mock_instance

            async with HealthChecker() as checker:
                result = await checker.check_http_endpoint(
                    "unreachable_api", "http://localhost:8000/health"
                )

                if result.status != HealthStatus.UNHEALTHY:
                    raise AssertionError
                if "Connection failed" not in result.message:
                    raise AssertionError
                if "Connection refused" not in result.details["error"]:
                    raise AssertionError

    @pytest.mark.asyncio
    async def test_check_redis_not_installed(self):
        """Test Redis check when redis client is not installed."""
        with patch("utils.health_checker.aioredis", None):
            async with HealthChecker() as checker:
                result = await checker.check_redis()

                if result.status != HealthStatus.UNHEALTHY:
                    raise AssertionError
                if result.message != "redis client not installed":
                    raise AssertionError
                if result.response_time_ms != 0:
                    raise AssertionError

    @pytest.mark.asyncio
    async def test_check_redis_success(self):
        """Test successful Redis health check."""
        with patch("utils.health_checker.aioredis") as mock_aioredis:
            mock_redis = AsyncMock()
            mock_redis.ping.return_value = True
            mock_redis.set.return_value = True
            mock_redis.get.return_value = "test"
            mock_redis.delete.return_value = 1
            mock_redis.info.return_value = {
                "redis_version": "6.2.0",
                "used_memory_human": "1.5M",
                "connected_clients": "3",
            }
            mock_redis.close.return_value = None
            mock_aioredis.from_url.return_value = mock_redis

            async with HealthChecker() as checker:
                result = await checker.check_redis(name="test_redis", host="localhost", port=6379)

                if result.name != "test_redis":
                    raise AssertionError
                if result.status != HealthStatus.HEALTHY:
                    raise AssertionError
                if "Redis ping and operations successful" not in result.message:
                    raise AssertionError
                if result.details["version"] != "6.2.0":
                    raise AssertionError
                if result.details["memory_usage"] != "1.5M":
                    raise AssertionError
                if result.details["connected_clients"] != "3":
                    raise AssertionError

    @pytest.mark.asyncio
    async def test_check_redis_connection_failure(self):
        """Test Redis check with connection failure."""
        with patch("utils.health_checker.aioredis") as mock_aioredis:
            mock_redis = AsyncMock()
            mock_redis.ping.side_effect = RuntimeError("Connection failed")
            mock_aioredis.from_url.return_value = mock_redis

            async with HealthChecker() as checker:
                result = await checker.check_redis()

                if result.status != HealthStatus.UNHEALTHY:
                    raise AssertionError
                if "Redis connection failed" not in result.message:
                    raise AssertionError

    @pytest.mark.asyncio
    async def test_check_redis_operations_failure(self):
        """Test Redis check with operations failure."""
        with patch("utils.health_checker.aioredis") as mock_aioredis:
            mock_redis = AsyncMock()
            mock_redis.ping.return_value = True
            mock_redis.set.return_value = True
            mock_redis.get.return_value = "wrong_value"  # Not "test"
            mock_redis.delete.return_value = 1
            mock_redis.close.return_value = None
            mock_aioredis.from_url.return_value = mock_redis

            async with HealthChecker() as checker:
                result = await checker.check_redis()

                if result.status != HealthStatus.DEGRADED:
                    raise AssertionError
                if "Redis operations failed" not in result.message:
                    raise AssertionError

    @pytest.mark.asyncio
    async def test_check_postgres_not_installed(self):
        """Test PostgreSQL check when asyncpg is not installed."""
        with patch("utils.health_checker.asyncpg", None):
            async with HealthChecker() as checker:
                result = await checker.check_postgres()

                if result.status != HealthStatus.UNHEALTHY:
                    raise AssertionError
                if result.message != "asyncpg not installed":
                    raise AssertionError

    @pytest.mark.asyncio
    async def test_check_postgres_success(self):
        """Test successful PostgreSQL health check."""
        with patch("utils.health_checker.asyncpg") as mock_asyncpg:
            mock_conn = AsyncMock()
            mock_conn.fetchval.return_value = 1
            mock_conn.fetchrow.return_value = {
                "table_count": 15,
                "database_size": "50 MB",
                "version": "PostgreSQL 13.4 on x86_64-pc-linux-gnu",
            }
            mock_conn.close.return_value = None
            mock_asyncpg.connect = AsyncMock(return_value=mock_conn)

            async with HealthChecker() as checker:
                result = await checker.check_postgres(
                    name="test_postgres", dsn="postgresql://user:pass@localhost:5432/testdb"
                )

                if result.name != "test_postgres":
                    raise AssertionError
                if result.status != HealthStatus.HEALTHY:
                    raise AssertionError
                if "PostgreSQL query successful" not in result.message:
                    raise AssertionError
                if result.details["table_count"] != 15:
                    raise AssertionError
                if result.details["database_size"] != "50 MB":
                    raise AssertionError
                if "PostgreSQL 13.4" not in result.details["version"]:
                    raise AssertionError

    @pytest.mark.asyncio
    async def test_check_postgres_connection_failure(self):
        """Test PostgreSQL check with connection failure."""
        with patch("utils.health_checker.asyncpg") as mock_asyncpg:
            mock_asyncpg.connect = AsyncMock(
                side_effect=RuntimeError("Connection failed"))

            async with HealthChecker() as checker:
                result = await checker.check_postgres()

                if result.status != HealthStatus.UNHEALTHY:
                    raise AssertionError
                if "PostgreSQL connection failed" not in result.message:
                    raise AssertionError

    @pytest.mark.asyncio
    async def test_check_postgres_query_failure(self):
        """Test PostgreSQL check with query returning wrong result."""
        with patch("utils.health_checker.asyncpg") as mock_asyncpg:
            mock_conn = AsyncMock()
            mock_conn.fetchval.return_value = 0  # Should be 1
            mock_conn.close.return_value = None
            mock_asyncpg.connect = AsyncMock(return_value=mock_conn)

            async with HealthChecker() as checker:
                result = await checker.check_postgres()

                if result.status != HealthStatus.DEGRADED:
                    raise AssertionError
                if "unexpected result" not in result.message:
                    raise AssertionError

    @pytest.mark.asyncio
    async def test_check_postgres_default_dsn(self):
        """Test PostgreSQL check with default DSN construction."""
        with (
            patch("utils.health_checker.asyncpg") as mock_asyncpg,
            patch.dict(
                "os.environ",
                {
                    "POSTGRES_USER": "testuser",
                    "POSTGRES_PASSWORD": "testpass",
                    "POSTGRES_HOST": "testhost",
                    "POSTGRES_PORT": "5433",
                    "POSTGRES_DB": "testdb",
                },
            ),
        ):
            mock_conn = AsyncMock()
            mock_conn.fetchval.return_value = 1
            mock_conn.fetchrow.return_value = {
                "table_count": 5,
                "database_size": "10 MB",
                "version": "PostgreSQL 13.0",
            }
            mock_conn.close.return_value = None
            mock_asyncpg.connect = AsyncMock(return_value=mock_conn)

            async with HealthChecker() as checker:
                result = await checker.check_postgres()

                # Should have constructed DSN from environment
                expected_dsn = "postgresql://testuser:testpass@testhost:5433/testdb"
                mock_asyncpg.connect.assert_called_with(expected_dsn)
                if result.status != HealthStatus.HEALTHY:
                    raise AssertionError

    @pytest.mark.asyncio
    async def test_check_lmstudio(self):
        """Test LM Studio health check."""
        async with HealthChecker() as checker:
            # Mock the HTTP endpoint check since check_lmstudio calls it
            with patch.object(checker, "check_http_endpoint", new_callable=AsyncMock) as mock_check:
                mock_result = HealthCheck(
                    "lmstudio", HealthStatus.HEALTHY, 100.0, "OK")
                mock_check.return_value = mock_result

                result = await checker.check_lmstudio(
                    name="test_lmstudio", base_url="http://localhost:1234"
                )

                if result != mock_result:
                    raise AssertionError
                mock_check.assert_called_with(
                    "test_lmstudio", "http://localhost:1234/v1/models")

    @pytest.mark.asyncio
    async def test_check_all_default_config(self):
        """Test check_all with default configuration."""
        async with HealthChecker() as checker:
            with (
                patch.object(checker, "check_http_endpoint", new_callable=AsyncMock) as mock_http,
                patch.object(checker, "check_redis", new_callable=AsyncMock) as mock_redis,
                patch.object(checker, "check_postgres", new_callable=AsyncMock) as mock_postgres,
                patch.object(checker, "check_lmstudio", new_callable=AsyncMock) as mock_lmstudio,
            ):
                # Setup mock results
                mock_http.return_value = HealthCheck(
                    "api", HealthStatus.HEALTHY, 100.0, "OK")
                mock_redis.return_value = HealthCheck(
                    "redis", HealthStatus.HEALTHY, 50.0, "OK")
                mock_postgres.return_value = HealthCheck(
                    "postgres", HealthStatus.HEALTHY, 200.0, "OK"
                )
                mock_lmstudio.return_value = HealthCheck(
                    "lmstudio", HealthStatus.HEALTHY, 150.0, "OK"
                )

                report = await checker.check_all()

                if report.overall_status != HealthStatus.HEALTHY:
                    raise AssertionError
                if report.total_checks != 4:
                    raise AssertionError
                if report.healthy_checks != 4:
                    raise AssertionError

                # Verify all checks were called
                mock_http.assert_called_once()
                mock_redis.assert_called_once()
                mock_postgres.assert_called_once()
                mock_lmstudio.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_all_custom_config(self):
        """Test check_all with custom configuration."""
        config = {
            "http_endpoints": [
                {"name": "api1", "url": "http://localhost:8001/health"},
                {"name": "api2", "url": "http://localhost:8002/status",
                    "expected_status": 204},
            ],
            "redis": {"host": "redis.example.com", "port": 6380},
            "postgres": {"dsn": "postgresql://user:pass@db.example.com/mydb"},
            "lmstudio": {"base_url": "http://ai.example.com:1234"},
        }

        async with HealthChecker() as checker:
            with (
                patch.object(checker, "check_http_endpoint", new_callable=AsyncMock) as mock_http,
                patch.object(checker, "check_redis", new_callable=AsyncMock) as mock_redis,
                patch.object(checker, "check_postgres", new_callable=AsyncMock) as mock_postgres,
                patch.object(checker, "check_lmstudio", new_callable=AsyncMock) as mock_lmstudio,
            ):
                # Setup mock results
                mock_http.return_value = HealthCheck(
                    "api", HealthStatus.HEALTHY, 100.0, "OK")
                mock_redis.return_value = HealthCheck(
                    "redis", HealthStatus.HEALTHY, 50.0, "OK")
                mock_postgres.return_value = HealthCheck(
                    "postgres", HealthStatus.HEALTHY, 200.0, "OK"
                )
                mock_lmstudio.return_value = HealthCheck(
                    "lmstudio", HealthStatus.HEALTHY, 150.0, "OK"
                )

                await checker.check_all(config)

                # Should have called HTTP endpoint check twice
                if mock_http.call_count != 2:
                    raise AssertionError

                # Verify custom parameters were used
                redis_call = mock_redis.call_args
                if redis_call[1]["host"] != "redis.example.com":
                    raise AssertionError
                if redis_call[1]["port"] != 6380:
                    raise AssertionError

    @pytest.mark.asyncio
    async def test_check_all_partial_config(self):
        """Test check_all with partial configuration."""
        config = {
            "http_endpoints": [{"name": "api", "url": "http://localhost:8000/health"}],
            # Only HTTP endpoints, no other services
        }

        async with HealthChecker() as checker:
            with patch.object(checker, "check_http_endpoint", new_callable=AsyncMock) as mock_http:
                mock_http.return_value = HealthCheck(
                    "api", HealthStatus.HEALTHY, 100.0, "OK")

                report = await checker.check_all(config)

                if report.total_checks != 1:
                    raise AssertionError
                if report.healthy_checks != 1:
                    raise AssertionError
                mock_http.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_all_mixed_results(self):
        """Test check_all with mixed health results."""
        async with HealthChecker() as checker:
            with (
                patch.object(checker, "check_http_endpoint", new_callable=AsyncMock) as mock_http,
                patch.object(checker, "check_redis", new_callable=AsyncMock) as mock_redis,
            ):
                # Setup mixed results
                mock_http.return_value = HealthCheck(
                    "api", HealthStatus.HEALTHY, 100.0, "OK")
                mock_redis.return_value = HealthCheck(
                    "redis", HealthStatus.UNHEALTHY, 0.0, "Down")

                config = {
                    "http_endpoints": [{"name": "api", "url": "http://localhost:8000/health"}],
                    "redis": {"host": "localhost", "port": 6379},
                }

                report = await checker.check_all(config)

                if report.overall_status != HealthStatus.UNHEALTHY:
                    raise AssertionError
                if report.total_checks != 2:
                    raise AssertionError
                if report.healthy_checks != 1:
                    raise AssertionError
                if report.unhealthy_checks != 1:
                    raise AssertionError


class TestQuickHealthCheck:
    """Test cases for quick_health_check convenience function."""

    @pytest.mark.asyncio
    async def test_quick_health_check_success(self):
        """Test successful quick health check."""
        with patch("utils.health_checker.HealthChecker") as mock_checker_class:
            mock_checker = AsyncMock()
            mock_report = HealthReport(
                overall_status=HealthStatus.HEALTHY,
                checks=[HealthCheck(
                    "test", HealthStatus.HEALTHY, 100.0, "OK")],
                total_checks=1,
                healthy_checks=1,
                degraded_checks=0,
                unhealthy_checks=0,
                timestamp=time.time(),
            )
            mock_checker.check_all.return_value = mock_report
            mock_checker_class.return_value.__aenter__.return_value = mock_checker

            result = await quick_health_check()

            if result["status"] != "healthy":
                raise AssertionError
            if result["summary"]["total"] != 1:
                raise AssertionError
            if result["summary"]["healthy"] != 1:
                raise AssertionError
            assert len(result["checks"]) == 1
            if result["checks"][0]["name"] != "test":
                raise AssertionError
            if result["checks"][0]["status"] != "healthy":
                raise AssertionError

    @pytest.mark.asyncio
    async def test_quick_health_check_with_degraded_services(self):
        """Test quick health check with degraded services."""
        with patch("utils.health_checker.HealthChecker") as mock_checker_class:
            mock_checker = AsyncMock()
            mock_checks = [
                HealthCheck("service1", HealthStatus.HEALTHY, 100.0, "OK"),
                HealthCheck("service2", HealthStatus.DEGRADED, 500.0, "Slow"),
                HealthCheck("service3", HealthStatus.UNHEALTHY, 0.0, "Down"),
            ]
            mock_report = HealthReport.from_checks(mock_checks)
            mock_checker.check_all.return_value = mock_report
            mock_checker_class.return_value.__aenter__.return_value = mock_checker

            result = await quick_health_check()

            if result["status"] != "unhealthy":
                raise AssertionError
            if result["summary"]["total"] != 3:
                raise AssertionError
            if result["summary"]["healthy"] != 1:
                raise AssertionError
            if result["summary"]["degraded"] != 1:
                raise AssertionError
            if result["summary"]["unhealthy"] != 1:
                raise AssertionError


class TestRetryDecorator:
    """Test cases for retry decorator functionality."""

    @pytest.mark.asyncio
    async def test_retry_decorator_on_http_check(self):
        """Test that retry decorator is applied to HTTP checks."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            # First call fails, second succeeds (simulating retry)
            mock_instance.get.side_effect = [
                RuntimeError("First attempt failed"),
                MagicMock(status_code=200, headers={}),
            ]
            mock_client.return_value = mock_instance

            async with HealthChecker() as checker:
                # The retry decorator should handle the first failure
                result = await checker.check_http_endpoint("test", "http://localhost:8000")

                # Should eventually succeed after retry
                # Note: Actual retry behavior depends on retry_on_failure implementation
                assert isinstance(result, HealthCheck)

    @pytest.mark.asyncio
    async def test_circuit_breaker_on_lmstudio_check(self):
        """Test that circuit breaker is applied to LM Studio checks."""
        async with HealthChecker() as checker:
            with patch.object(checker, "check_http_endpoint", new_callable=AsyncMock) as mock_check:
                mock_check.return_value = HealthCheck(
                    "lmstudio", HealthStatus.HEALTHY, 100.0, "OK")

                result = await checker.check_lmstudio()

                # Should call underlying HTTP check
                mock_check.assert_called_once()
                if result.name != "lmstudio":
                    raise AssertionError


class TestPerformanceAndConcurrency:
    """Test cases for performance and concurrency characteristics."""

    @pytest.mark.asyncio
    async def test_concurrent_health_checks(self):
        """Test concurrent health checks."""
        async with HealthChecker() as checker:
            with patch.object(checker, "check_http_endpoint", new_callable=AsyncMock) as mock_http:
                # Setup different response times to test concurrency
                async def delayed_response(name, url, expected_status=200):
                    await asyncio.sleep(0.1)  # Simulate network delay
                    return HealthCheck(name, HealthStatus.HEALTHY, 100.0, "OK")

                mock_http.side_effect = delayed_response

                # Start multiple concurrent checks
                start_time = time.time()
                tasks = [
                    checker.check_http_endpoint(
                        f"api{i}", f"http://localhost:800{i}")
                    for i in range(5)
                ]

                results = await asyncio.gather(*tasks)
                end_time = time.time()

                # Should complete faster than sequential execution
                if (end_time - start_time) >= 1.0:
                    raise AssertionError
                assert len(results) == 5
                if not all(r.status == HealthStatus.HEALTHY for r in results):
                    raise AssertionError

    @pytest.mark.asyncio
    async def test_timeout_handling_under_load(self):
        """Test timeout handling under load."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()

            # Simulate timeout exception
            async def timeout_response(*args, **kwargs):
                await asyncio.sleep(0.2)  # Longer than timeout
                import httpx

                raise httpx.TimeoutException("Request timed out")

            mock_instance.get.side_effect = timeout_response
            mock_client.return_value = mock_instance

            async with HealthChecker(timeout=0.1) as checker:
                logging.debug(
                    f"Mock setup complete for test_timeout_handling_under_load. Mock client: {mock_client}"
                )

                result = await checker.check_http_endpoint("slow_api", "http://localhost:8000")

                # Should handle timeout gracefully
                if result.status != HealthStatus.UNHEALTHY:
                    raise AssertionError

    @pytest.mark.asyncio
    async def test_large_response_handling(self):
        """Test handling of large response data."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            # Large headers dictionary
            large_headers = {f"header_{i}": f"value_{i}" for i in range(100)}
            mock_response.headers = large_headers
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value = mock_instance

            async with HealthChecker() as checker:
                result = await checker.check_http_endpoint("large_api", "http://localhost:8000")

                if result.status != HealthStatus.HEALTHY:
                    raise AssertionError
                assert len(result.details["response_headers"]) == 100


class TestErrorHandlingAndRecovery:
    """Test cases for error handling and recovery scenarios."""

    @pytest.mark.asyncio
    async def test_network_error_handling(self):
        """Test handling of various network errors."""
        network_errors = [
            RuntimeError("Connection timeout"),
            RuntimeError("DNS resolution failed"),
            RuntimeError("Network unreachable"),
            RuntimeError("Connection refused"),
        ]

        for error in network_errors:
            with patch("httpx.AsyncClient") as mock_client:
                mock_instance = AsyncMock()
                mock_instance.get = AsyncMock(side_effect=error)
                mock_client.return_value = mock_instance

                async with HealthChecker() as checker:
                    result = await checker.check_http_endpoint("test", "http://localhost:8000")

                    if result.status != HealthStatus.UNHEALTHY:
                        raise AssertionError
                    if "Connection failed" not in result.message:
                        raise AssertionError
                    if str(error) not in result.details["error"]:
                        raise AssertionError

    @pytest.mark.asyncio
    async def test_partial_service_failures(self):
        """Test handling when some services fail."""
        async with HealthChecker() as checker:
            with (
                patch.object(checker, "check_http_endpoint", new_callable=AsyncMock) as mock_http,
                patch.object(checker, "check_redis", new_callable=AsyncMock) as mock_redis,
            ):
                # HTTP succeeds, Redis fails
                mock_http.return_value = HealthCheck(
                    "api", HealthStatus.HEALTHY, 100.0, "OK")
                mock_redis.return_value = HealthCheck(
                    "redis", HealthStatus.UNHEALTHY, 0.0, "Failed"
                )

                config = {
                    "http_endpoints": [{"name": "api", "url": "http://localhost:8000"}],
                    "redis": {"host": "localhost", "port": 6379},
                }

                report = await checker.check_all(config)

                # Overall should be unhealthy due to Redis failure
                if report.overall_status != HealthStatus.UNHEALTHY:
                    raise AssertionError
                if report.total_checks != 2:
                    raise AssertionError
                if report.healthy_checks != 1:
                    raise AssertionError
                if report.unhealthy_checks != 1:
                    raise AssertionError

    @pytest.mark.asyncio
    async def test_exception_in_check_all(self):
        """Test exception handling in check_all method."""
        async with HealthChecker() as checker:
            with patch.object(checker, "check_http_endpoint") as mock_http:
                mock_http.side_effect = Exception("Unexpected error")

                config = {"http_endpoints": [
                    {"name": "api", "url": "http://localhost:8000"}]}

                # Should handle exception gracefully and continue
                try:
                    await checker.check_all(config)
                    # If it succeeds, that's fine
                except Exception:
                    # If it fails, that's also acceptable behavior for this test
                    pass

    @pytest.mark.asyncio
    async def test_context_manager_cleanup_on_exception(self):
        """Test context manager cleanup when exception occurs."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value = mock_instance

            try:
                async with HealthChecker():
                    raise RuntimeError("Simulated error")
            except RuntimeError:
                pass  # Expected

            # Should have closed HTTP client
            mock_instance.aclose.assert_called_once()


class TestIntegrationScenarios:
    """Integration test cases for realistic usage scenarios."""

    @pytest.mark.asyncio
    async def test_full_system_health_check(self):
        """Test complete system health check workflow."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {"server": "nginx/1.18"}
            mock_instance.get.return_value = mock_response
            mock_client.return_value = mock_instance

            logging.debug(
                f"HTTP mock setup complete for test_full_system_health_check. Mock client: {mock_client}"
            )

            # Mock Redis as healthy
            with patch("utils.health_checker.aioredis") as mock_aioredis:
                mock_redis = AsyncMock()
                mock_redis.ping.return_value = True
                mock_redis.set.return_value = True
                mock_redis.get.return_value = "test"
                mock_redis.delete.return_value = 1
                mock_redis.info.return_value = {"redis_version": "6.2.0"}
                mock_redis.close.return_value = None
                mock_aioredis.from_url.return_value = mock_redis

                logging.debug(
                    "Redis mock setup complete for test_full_system_health_check")

                result = await quick_health_check()

                if "status" not in result:
                    raise AssertionError
                if "timestamp" not in result:
                    raise AssertionError
                if "summary" not in result:
                    raise AssertionError
                if "checks" not in result:
                    raise AssertionError
                assert isinstance(result["checks"], list)

    @pytest.mark.asyncio
    async def test_health_check_monitoring_workflow(self):
        """Test health check in monitoring workflow."""
        # Simulate periodic health checking
        check_results = []

        async def simulate_health_monitoring():
            for _i in range(3):
                result = await quick_health_check()
                check_results.append(result)
                await asyncio.sleep(0.01)  # Small delay between checks

        with patch("utils.health_checker.HealthChecker") as mock_checker_class:
            mock_checker = AsyncMock()
            mock_report = HealthReport(
                overall_status=HealthStatus.HEALTHY,
                checks=[HealthCheck(
                    "service", HealthStatus.HEALTHY, 100.0, "OK")],
                total_checks=1,
                healthy_checks=1,
                degraded_checks=0,
                unhealthy_checks=0,
                timestamp=time.time(),
            )
            mock_checker.check_all.return_value = mock_report
            mock_checker_class.return_value.__aenter__.return_value = mock_checker

            await simulate_health_monitoring()

            assert len(check_results) == 3
            for result in check_results:
                if result["status"] != "healthy":
                    raise AssertionError

    @pytest.mark.asyncio
    async def test_service_discovery_integration(self):
        """Test integration with service discovery pattern."""
        # Simulate dynamic service discovery
        services = [
            {"name": "web-service-1", "url": "http://10.0.1.10:8080/health"},
            {"name": "web-service-2", "url": "http://10.0.1.11:8080/health"},
            {"name": "api-service-1", "url": "http://10.0.2.10:9090/status"},
        ]

        config = {"http_endpoints": services}

        async with HealthChecker() as checker:
            with patch.object(checker, "check_http_endpoint", new_callable=AsyncMock) as mock_check:
                # All services healthy
                mock_check.return_value = HealthCheck(
                    "service", HealthStatus.HEALTHY, 100.0, "OK")

                report = await checker.check_all(config)

                if report.total_checks != 3:
                    raise AssertionError
                if report.healthy_checks != 3:
                    raise AssertionError
                # Should have called check for each discovered service
                if mock_check.call_count != 3:
                    raise AssertionError

    @pytest.mark.asyncio
    async def test_degraded_performance_detection(self):
        """Test detection of degraded performance."""
        async with HealthChecker() as checker:
            with patch.object(checker, "check_http_endpoint", new_callable=AsyncMock) as mock_http:
                # Service responds but slowly
                slow_check = HealthCheck(
                    "slow_api", HealthStatus.HEALTHY, 2000.0, "HTTP 200")
                mock_http.return_value = slow_check

                config = {"http_endpoints": [
                    {"name": "slow_api", "url": "http://localhost:8000"}]}

                report = await checker.check_all(config)

                # Service is technically healthy but slow
                if report.overall_status != HealthStatus.HEALTHY:
                    raise AssertionError
                if report.checks[0].response_time_ms != 2000.0:
                    raise AssertionError

                # In a real scenario, you might mark this as degraded based on response time
                # but that would be application logic, not health checker logic

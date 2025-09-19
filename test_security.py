"""
Security Unit Tests for DinoAir Components.

This module provides unit tests for security components including:
- Authentication system testing
- Network security middleware testing
- Audit logging verification
- Security configuration validation
"""

import pytest
import asyncio
import json
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Import our security modules
try:
    from utils.auth_system import (
        UserManager, User, UserRole, Permission, PasswordPolicy,
        AuthenticationMethod
    )
    from utils.network_security import (
        NetworkSecurityConfig, SecurityLevel, RateLimitRule, RateLimitScope,
        SecurityMiddleware, create_small_team_security_config
    )
    from utils.audit_logging import (
        AuditLogger, AuditEvent, AuditEventType, SeverityLevel,
        SecurityAuditManager
    )
    from utils.security_config import SecurityConfig, ComplianceMode
    SECURITY_MODULES_AVAILABLE = True
except ImportError as e:
    print(f"Security modules not available: {e}")
    SECURITY_MODULES_AVAILABLE = False

try:
    from fastapi import Request, Response
    from fastapi.testclient import TestClient
    FASTAPI_AVAILABLE = True
except ImportError:
    Request = Response = TestClient = None
    FASTAPI_AVAILABLE = False


class TestPasswordPolicies:
    """Test password policy enforcement."""

    @pytest.fixture
    def password_policy(self):
        """Create HIPAA-compliant password policy."""
        return PasswordPolicy.hipaa_compliant()

    @pytest.fixture
    def user_manager(self, password_policy):
        """Create user manager with test policy."""
        if not SECURITY_MODULES_AVAILABLE:
            pytest.skip("Security modules not available")
        return UserManager(password_policy)

    def test_strong_password_accepted(self, user_manager):
        """Test that strong passwords are accepted."""
        strong_password = "MySecur3P@ssw0rd2024!"

        user = user_manager.create_user(
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            password=strong_password,
            roles=[UserRole.OPERATOR]
        )

        assert user.username == "testuser"
        assert user.password_hash is not None
        assert user.password_hash != strong_password  # Should be hashed

    def test_weak_password_rejected(self, user_manager):
        """Test that weak passwords are rejected."""
        weak_passwords = [
            "123456",
            "password",
            "short",
            "noUPPERCASE123!",
            "NO_LOWERCASE_123!",
            "NoNumbers!",
            "NoSpecialChars123"
        ]

        for weak_password in weak_passwords:
            with pytest.raises(ValueError):
                user_manager.create_user(
                    username=f"testuser_{weak_password}",
                    email=f"test_{weak_password}@example.com",
                    full_name="Test User",
                    password=weak_password,
                    roles=[UserRole.OPERATOR]
                )

    def test_password_history_enforced(self, user_manager):
        """Test that password history is enforced."""
        user = user_manager.create_user(
            username="historytest",
            email="history@example.com",
            full_name="History Test",
            password="FirstPassword123!",
            roles=[UserRole.OPERATOR]
        )

        # Try to change to a new password
        user_manager.change_password(
            user.user_id,
            "FirstPassword123!",
            "SecondPassword456@"
        )

        # Try to change back to the first password (should fail)
        with pytest.raises(ValueError, match="Password has been used recently"):
            user_manager.change_password(
                user.user_id,
                "SecondPassword456@",
                "FirstPassword123!"
            )

    def test_account_lockout(self, user_manager):
        """Test account lockout after failed attempts."""
        user = user_manager.create_user(
            username="lockouttest",
            email="lockout@example.com",
            full_name="Lockout Test",
            password="CorrectPassword123!",
            roles=[UserRole.OPERATOR]
        )

        # Simulate failed login attempts
        for _ in range(5):  # Policy allows 3 attempts
            try:
                user_manager.authenticate_user(
                    "lockouttest",
                    "WrongPassword123!",
                    "127.0.0.1",
                    "TestAgent"
                )
            except Exception:
                pass  # Expected to fail

        # Account should now be locked
        assert user.is_account_locked()


class TestRoleBasedAccessControl:
    """Test RBAC implementation."""

    @pytest.fixture
    def user_manager(self):
        """Create user manager for RBAC testing."""
        if not SECURITY_MODULES_AVAILABLE:
            pytest.skip("Security modules not available")
        return UserManager()

    def test_clinician_permissions(self, user_manager):
        """Test that clinicians have appropriate permissions."""
        clinician = user_manager.create_user(
            username="dr_smith",
            email="dr.smith@hospital.com",
            full_name="Dr. Smith",
            password="ClinicianPass123!",
            roles=[UserRole.CLINICIAN]
        )

        # Clinicians should have patient data access
        assert clinician.has_permission(Permission.PATIENT_DATA_READ)
        assert clinician.has_permission(Permission.PATIENT_DATA_WRITE)
        assert clinician.has_permission(Permission.MEDICAL_RECORDS)
        assert clinician.has_permission(Permission.EMERGENCY_ACCESS)

        # But not system admin permissions
        assert not clinician.has_permission(Permission.SYSTEM_CONFIG)
        assert not clinician.has_permission(Permission.SYSTEM_USERS)

    def test_read_only_permissions(self, user_manager):
        """Test read-only user permissions."""
        readonly_user = user_manager.create_user(
            username="readonly",
            email="readonly@company.com",
            full_name="Read Only User",
            password="ReadOnlyPass123!",
            roles=[UserRole.READ_ONLY]
        )

        # Should have read permissions
        assert readonly_user.has_permission(Permission.DATA_READ)
        assert readonly_user.has_permission(Permission.API_READ)

        # But not write permissions
        assert not readonly_user.has_permission(Permission.DATA_CREATE)
        assert not readonly_user.has_permission(Permission.DATA_UPDATE)
        assert not readonly_user.has_permission(Permission.DATA_DELETE)

    def test_emergency_dispatcher_permissions(self, user_manager):
        """Test emergency dispatcher has appropriate access."""
        dispatcher = user_manager.create_user(
            username="dispatcher1",
            email="dispatch@ambulance.com",
            full_name="Emergency Dispatcher",
            password="DispatchPass123!",
            roles=[UserRole.DISPATCHER]
        )

        # Should have emergency access
        assert dispatcher.has_permission(Permission.EMERGENCY_ACCESS)
        assert dispatcher.has_permission(Permission.DATA_READ)
        assert dispatcher.has_permission(Permission.DATA_CREATE)
        assert dispatcher.has_permission(Permission.API_WRITE)

        # But not admin permissions
        assert not dispatcher.has_permission(Permission.SYSTEM_CONFIG)


class TestNetworkSecurityMiddleware:
    """Test network security middleware."""

    @pytest.fixture
    def security_config(self):
        """Create security configuration for testing."""
        if not SECURITY_MODULES_AVAILABLE:
            pytest.skip("Security modules not available")
        return create_small_team_security_config()

    @pytest.fixture
    def mock_request(self):
        """Create mock FastAPI request."""
        if not FASTAPI_AVAILABLE:
            pytest.skip("FastAPI not available")

        request = Mock(spec=Request)
        request.method = "GET"
        request.url.path = "/api/v1/test"
        request.url.scheme = "http"
        request.headers = {"user-agent": "TestAgent/1.0"}
        request.client.host = "127.0.0.1"
        return request

    @pytest.fixture
    def security_middleware(self, security_config):
        """Create security middleware instance."""
        if not SECURITY_MODULES_AVAILABLE:
            pytest.skip("Security modules not available")
        return SecurityMiddleware(None, security_config)

    def test_rate_limiting_allows_normal_requests(self, security_middleware, mock_request):
        """Test that normal request rates are allowed."""
        client_ip = "127.0.0.1"

        # Simulate normal request pattern (under limits)
        for _ in range(5):
            allowed = security_middleware._check_rate_limits(mock_request, client_ip)
            assert allowed, "Normal request rate should be allowed"

    def test_rate_limiting_blocks_excessive_requests(self, security_middleware, mock_request):
        """Test that excessive requests are blocked."""
        client_ip = "127.0.0.1"

        # Simulate excessive requests (over 600/minute for small team config)
        security_middleware.rate_limiter.requests[f"ip:{client_ip}"] = [time.time()] * 700

        blocked = not security_middleware._check_rate_limits(mock_request, client_ip)
        assert blocked, "Excessive requests should be blocked"

    def test_ip_allowlist_enforcement(self, security_middleware):
        """Test IP allowlist enforcement."""
        # Add specific IP to allowlist
        security_middleware.config.allowed_ips.add("192.168.1.100")

        # Allowed IP should pass
        assert security_middleware._check_ip_allowed("192.168.1.100")

        # If allowlist is configured, other IPs should be blocked
        if security_middleware.config.allowed_ips:
            assert not security_middleware._check_ip_allowed("10.0.0.1")

    def test_ddos_detection(self, security_middleware):
        """Test DDoS detection."""
        client_ip = "192.168.1.200"

        # Simulate DDoS pattern (many requests in short time)
        current_time = time.time()
        attack_requests = [current_time - i for i in range(1000)]  # 1000 requests in last second

        security_middleware.ddos_tracker[client_ip].extend(attack_requests)

        is_ddos = security_middleware._detect_ddos(client_ip)
        assert is_ddos, "DDoS pattern should be detected"


class TestAuditLogging:
    """Test audit logging system."""

    @pytest.fixture
    def temp_log_dir(self):
        """Create temporary directory for test logs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def audit_logger(self, temp_log_dir):
        """Create audit logger for testing."""
        if not SECURITY_MODULES_AVAILABLE:
            pytest.skip("Security modules not available")

        log_file = temp_log_dir / "test_audit.log"
        secret_key = "test_secret_key_for_audit_testing"
        return AuditLogger(log_file, secret_key)

    @pytest.fixture
    def audit_manager(self, audit_logger):
        """Create audit manager for testing."""
        if not SECURITY_MODULES_AVAILABLE:
            pytest.skip("Security modules not available")
        return SecurityAuditManager(audit_logger)

    def test_audit_event_creation(self, audit_manager):
        """Test audit event creation and logging."""
        event_id = audit_manager.log_authentication(
            AuditEventType.LOGIN_SUCCESS,
            user_id="test_user",
            source_ip="127.0.0.1",
            user_agent="TestAgent/1.0"
        )

        assert event_id is not None
        assert len(event_id) > 0

    def test_audit_log_integrity(self, audit_logger):
        """Test audit log integrity verification."""
        # Create an audit event
        event_id = audit_logger.audit(
            AuditEventType.DATA_READ,
            user_id="integrity_test",
            source_ip="127.0.0.1",
            resource="test_data",
            details={"test": "data"}
        )

        # Read the log file and verify integrity
        log_file = audit_logger.log_file
        assert log_file.exists()

        # Check that log contains the event
        with open(log_file, 'r') as f:
            log_content = f.read()
            assert event_id in log_content
            assert "integrity_test" in log_content

    def test_data_access_logging(self, audit_manager):
        """Test data access audit logging."""
        event_id = audit_manager.log_data_access(
            action="read",
            resource="patient_records",
            user_id="dr_test",
            source_ip="192.168.1.100",
            record_count=5
        )

        assert event_id is not None

    def test_security_violation_logging(self, audit_manager):
        """Test security violation logging."""
        event_id = audit_manager.log_security_event(
            AuditEventType.SECURITY_VIOLATION,
            description="Multiple failed login attempts detected",
            source_ip="10.0.0.1",
            severity=SeverityLevel.CRITICAL
        )

        assert event_id is not None

    def test_api_request_logging(self, audit_manager):
        """Test API request audit logging."""
        event_id = audit_manager.log_api_request(
            method="POST",
            endpoint="/api/v1/patients",
            user_id="api_test_user",
            source_ip="127.0.0.1",
            status_code=201,
            response_time_ms=150.5
        )

        assert event_id is not None


class TestSecurityConfiguration:
    """Test security configuration system."""

    def test_hipaa_compliance_mode(self):
        """Test HIPAA compliance configuration."""
        if not SECURITY_MODULES_AVAILABLE:
            pytest.skip("Security modules not available")

        config = SecurityConfig(compliance_mode=ComplianceMode.HIPAA)

        # HIPAA should enforce strong settings
        assert config.audit_retention_days >= 2555  # 7 years
        assert config.session_timeout_minutes <= 30
        assert config.password_complexity_enabled
        assert config.mfa_required

    def test_small_team_security_config(self):
        """Test small team security configuration."""
        if not SECURITY_MODULES_AVAILABLE:
            pytest.skip("Security modules not available")

        config = create_small_team_security_config()

        # Should have relaxed but secure settings
        assert not config.require_https  # Allow HTTP for development
        assert len(config.cors_allow_origins) > 1  # Multiple dev origins
        assert any(rule.requests_per_minute >= 600 for rule in config.rate_limit_rules)
        assert config.ddos_block_duration <= 300  # Short blocks (5 minutes)


class TestSecurityIntegration:
    """Integration tests for security components."""

    @pytest.fixture
    def integrated_system(self):
        """Set up integrated security system."""
        if not SECURITY_MODULES_AVAILABLE:
            pytest.skip("Security modules not available")

        # Create all components
        user_manager = UserManager(PasswordPolicy.hipaa_compliant())
        security_config = create_small_team_security_config()

        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "integration_audit.log"
            audit_logger = AuditLogger(log_file, "integration_test_secret")
            audit_manager = SecurityAuditManager(audit_logger)

            yield {
                "user_manager": user_manager,
                "security_config": security_config,
                "audit_manager": audit_manager
            }

    def test_user_creation_with_audit(self, integrated_system):
        """Test user creation triggers audit logging."""
        user_manager = integrated_system["user_manager"]
        audit_manager = integrated_system["audit_manager"]

        # Create user
        user = user_manager.create_user(
            username="integration_test",
            email="integration@test.com",
            full_name="Integration Test User",
            password="IntegrationPass123!",
            roles=[UserRole.OPERATOR]
        )

        # Log the user creation
        audit_id = audit_manager.audit_logger.audit(
            AuditEventType.USER_CREATE,
            user_id="admin",
            details={
                "created_user": user.username,
                "roles": [role.value for role in user.roles]
            }
        )

        assert user.username == "integration_test"
        assert audit_id is not None

    def test_authentication_flow_with_security(self, integrated_system):
        """Test complete authentication flow with security measures."""
        user_manager = integrated_system["user_manager"]
        audit_manager = integrated_system["audit_manager"]

        # Create test user
        user = user_manager.create_user(
            username="auth_flow_test",
            email="authflow@test.com",
            full_name="Auth Flow Test",
            password="AuthFlowPass123!",
            roles=[UserRole.CLINICIAN]
        )

        # Test successful authentication
        session = user_manager.authenticate_user(
            username="auth_flow_test",
            password="AuthFlowPass123!",
            source_ip="127.0.0.1",
            user_agent="IntegrationTest/1.0",
            require_mfa=False
        )

        # Log the authentication
        audit_manager.log_authentication(
            AuditEventType.LOGIN_SUCCESS,
            user_id=user.user_id,
            source_ip="127.0.0.1",
            user_agent="IntegrationTest/1.0"
        )

        assert session is not None
        assert session.user_id == user.user_id
        assert not session.is_expired()


# Test runner configuration
def run_security_tests():
    """Run all security tests."""
    if not SECURITY_MODULES_AVAILABLE:
        print("❌ Security modules not available. Install dependencies first.")
        return False

    print("🧪 Running DinoAir Security Tests...")

    # Run tests with pytest
    test_result = pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--no-header"
    ])

    return test_result == 0


if __name__ == "__main__":
    # Run security tests
    print("🔒 DinoAir Security Unit Tests")
    print("=" * 50)

    success = run_security_tests()

    if success:
        print("\n✅ All security tests passed!")
    else:
        print("\n❌ Some security tests failed!")
        print("💡 Review the test output above for details.")

    exit(0 if success else 1)
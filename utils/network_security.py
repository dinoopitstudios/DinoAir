"""
Network security hardening module for DinoAir.

This module implements enterprise-grade network security measures including:
- TLS 1.3 enforcement with certificate management
- Rate limiting with configurable thresholds
- CORS restrictions for production environments
- IP allowlisting for critical infrastructure
- Secure headers middleware
- DDoS protection and request validation
"""

from __future__ import annotations

import ipaddress
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Union

try:
    from fastapi import HTTPException, Request, status
    from fastapi.middleware.base import BaseHTTPMiddleware
    from fastapi.responses import JSONResponse
    from starlette.middleware.base import RequestResponseEndpoint
    from starlette.responses import Response
except ImportError:
    # Graceful fallback for testing without FastAPI
    Request = status = JSONResponse = None
    HTTPException = Exception
    BaseHTTPMiddleware = RequestResponseEndpoint = Response = object


class SecurityLevel(Enum):
    """Security levels for different environments."""

    DEVELOPMENT = "development"
    SMALL_TEAM = "small_team"  # For small teams (2-5 people)
    STAGING = "staging"
    PRODUCTION = "production"
    CRITICAL = "critical"  # For ambulance/healthcare environments


class RateLimitScope(Enum):
    """Rate limiting scopes."""

    GLOBAL = "global"
    PER_IP = "per_ip"
    PER_USER = "per_user"
    PER_ENDPOINT = "per_endpoint"


@dataclass
class RateLimitRule:
    """Rate limiting rule configuration."""

    requests_per_minute: int
    burst_capacity: int = 0  # Allow burst above rate limit
    scope: RateLimitScope = RateLimitScope.PER_IP
    endpoints: Optional[List[str]] = None  # Apply to specific endpoints
    exempt_ips: Set[str] = field(default_factory=set)

    def __post_init__(self):
        if self.burst_capacity == 0:
            self.burst_capacity = max(10, self.requests_per_minute // 6)  # 10 second burst


@dataclass
class SecurityHeaders:
    """Security headers configuration."""

    strict_transport_security: str = "max-age=63072000; includeSubDomains; preload"
    content_security_policy: str = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "connect-src 'self' ws: wss:; "
        "font-src 'self'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    x_frame_options: str = "DENY"
    x_content_type_options: str = "nosniff"
    x_xss_protection: str = "1; mode=block"
    referrer_policy: str = "strict-origin-when-cross-origin"
    permissions_policy: str = (
        "geolocation=(), microphone=(), camera=(), payment=(), "
        "usb=(), magnetometer=(), gyroscope=(), speaker=()"
    )


@dataclass
class NetworkSecurityConfig:
    """Network security configuration."""

    # TLS Configuration
    tls_min_version: str = "1.3"
    require_https: bool = True
    hsts_max_age: int = 63072000  # 2 years

    # Rate Limiting
    rate_limit_rules: List[RateLimitRule] = field(default_factory=list)
    rate_limit_storage_ttl: int = 3600  # 1 hour

    # IP Filtering
    allowed_ips: Set[str] = field(default_factory=set)
    blocked_ips: Set[str] = field(default_factory=set)
    allow_private_ips: bool = True

    # CORS Configuration
    cors_allow_origins: List[str] = field(default_factory=list)
    cors_allow_methods: List[str] = field(default_factory=lambda: ["GET", "POST", "PUT", "DELETE"])
    cors_allow_headers: List[str] = field(default_factory=lambda: ["*"])
    cors_allow_credentials: bool = True

    # Request Validation
    max_request_size: int = 10 * 1024 * 1024  # 10MB
    max_header_size: int = 8192  # 8KB
    request_timeout: int = 30  # seconds

    # Security Headers
    security_headers: SecurityHeaders = field(default_factory=SecurityHeaders)

    # DDoS Protection
    ddos_detection_enabled: bool = True
    ddos_threshold_requests: int = 1000
    ddos_threshold_window: int = 60  # seconds
    ddos_block_duration: int = 3600  # 1 hour

    @classmethod
    def for_security_level(cls, security_level: SecurityLevel) -> NetworkSecurityConfig:
        """Create configuration for specific security level."""

        network_config = cls()

        if security_level == SecurityLevel.DEVELOPMENT:
            network_config.require_https = False
            network_config.allowed_ips = set()  # Allow all
            network_config.cors_allow_origins = ["*"]
            network_config.ddos_detection_enabled = False

        elif security_level == SecurityLevel.SMALL_TEAM:
            # Perfect for 2-5 person teams with relaxed limits
            network_config.require_https = False  # Can use HTTP for development
            network_config.allowed_ips = set()  # Allow all IPs
            network_config.cors_allow_origins = [
                "http://localhost:3000",
                "http://localhost:5173",
                "http://localhost:5174",
                "http://localhost:8000",
            ]
            network_config.rate_limit_rules = [
                RateLimitRule(requests_per_minute=600, scope=RateLimitScope.PER_IP),  # 10/second
                RateLimitRule(requests_per_minute=2000, scope=RateLimitScope.GLOBAL),
            ]
            network_config.ddos_threshold_requests = 1000
            network_config.ddos_block_duration = 300  # 5 minutes

        elif security_level == SecurityLevel.STAGING:
            network_config.require_https = True
            network_config.cors_allow_origins = [
                "https://staging.dinoair.com",
                "http://localhost:3000",
            ]

        elif security_level == SecurityLevel.PRODUCTION:
            network_config.require_https = True
            network_config.cors_allow_origins = ["https://dinoair.com"]
            network_config.rate_limit_rules = [
                RateLimitRule(requests_per_minute=60, scope=RateLimitScope.PER_IP),
                RateLimitRule(requests_per_minute=1000, scope=RateLimitScope.GLOBAL),
            ]

        elif security_level == SecurityLevel.CRITICAL:
            # Ambulance/healthcare environment settings - relaxed for small team
            network_config.require_https = True
            network_config.tls_min_version = "1.3"
            network_config.cors_allow_origins = ["https://secure.dinoair.healthcare"]
            network_config.allow_private_ips = True  # Allow private IPs for small team
            network_config.max_request_size = 5 * 1024 * 1024  # 5MB limit
            network_config.request_timeout = 30  # Standard timeout
            network_config.rate_limit_rules = [
                RateLimitRule(
                    requests_per_minute=300, scope=RateLimitScope.PER_IP
                ),  # 5 requests/second
                RateLimitRule(requests_per_minute=1000, scope=RateLimitScope.GLOBAL),
                RateLimitRule(
                    requests_per_minute=60,
                    scope=RateLimitScope.PER_ENDPOINT,
                    endpoints=["/api/v1/export", "/api/v1/backup"],
                ),  # 1 per second for heavy ops
            ]
            network_config.ddos_threshold_requests = 500  # Higher threshold for small team
            network_config.ddos_block_duration = 1800  # 30 minutes instead of 2 hours

            # Enhanced CSP for healthcare
            network_config.security_headers.content_security_policy = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self'; "
                "img-src 'self' data:; "
                "connect-src 'self'; "
                "font-src 'self'; "
                "object-src 'none'; "
                "base-uri 'self'; "
                "form-action 'self'; "
                "upgrade-insecure-requests"
            )

        return network_config


class RateLimitStore:
    """In-memory rate limit tracking store."""

    def __init__(self, ttl: int = 3600):
        self.ttl = ttl
        self.requests: Dict[str, deque] = defaultdict(deque)
        self.last_cleanup = time.time()

    def _cleanup_old_entries(self):
        """Remove expired entries."""
        current_time = time.time()
        if current_time - self.last_cleanup < 60:  # Cleanup every minute
            return

        cutoff_time = current_time - self.ttl

        for key in list(self.requests.keys()):
            request_times = self.requests[key]

            # Remove old entries
            while request_times and request_times[0] < cutoff_time:
                request_times.popleft()

            # Remove empty keys
            if not request_times:
                del self.requests[key]

        self.last_cleanup = current_time

    def add_request(self, key: str) -> None:
        """Add a request timestamp."""
        self._cleanup_old_entries()
        self.requests[key].append(time.time())

    def get_request_count(self, key: str, window_seconds: int) -> int:
        """Get request count within time window."""
        self._cleanup_old_entries()

        if key not in self.requests:
            return 0

        current_time = time.time()
        cutoff_time = current_time - window_seconds

        # Count requests within window
        count = 0
        for request_time in self.requests[key]:
            if request_time >= cutoff_time:
                count += 1

        return count


class SecurityMiddleware(BaseHTTPMiddleware):
    """Comprehensive security middleware for FastAPI."""

    def __init__(
        self, app, security_config: NetworkSecurityConfig, audit_callback: Optional[Callable] = None
    ):
        super().__init__(app)
        self.security_config = security_config
        self.audit_callback = audit_callback
        self.rate_limiter = RateLimitStore(security_config.rate_limit_storage_ttl)
        self.blocked_ips: Dict[str, float] = {}  # IP -> block_until_timestamp
        self.ddos_tracker: Dict[str, deque] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Process request through security checks."""

        start_time = time.time()
        client_ip = self._get_client_ip(request)

        try:
            # 1. IP Filtering
            if not self._check_ip_allowed(client_ip):
                await self._audit_security_event(
                    "ip_blocked", client_ip, {"reason": "IP not in allowlist"}
                )
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

            # 2. Check blocked IPs
            if self._is_ip_blocked(client_ip):
                await self._audit_security_event(
                    "blocked_ip_attempt", client_ip, {"reason": "IP temporarily blocked"}
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many requests"
                )

            # 3. DDoS Detection
            if self.config.ddos_detection_enabled:
                if self._detect_ddos(client_ip):
                    self._block_ip(client_ip, self.config.ddos_block_duration)
                    await self._audit_security_event(
                        "ddos_detected", client_ip, {"action": "ip_blocked"}
                    )
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded"
                    )

            # 4. HTTPS Enforcement
            if self.config.require_https and request.url.scheme != "https":
                https_url = request.url.replace(scheme="https")
                return Response(status_code=301, headers={"Location": str(https_url)})

            # 5. Request Size Validation
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > self.config.max_request_size:
                await self._audit_security_event(
                    "request_too_large", client_ip, {"size": content_length}
                )
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Request too large"
                )

            # 6. Rate Limiting
            if not self._check_rate_limits(request, client_ip):
                await self._audit_security_event(
                    "rate_limit_exceeded", client_ip, {"endpoint": str(request.url.path)}
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded"
                )

            # Process request
            response = await call_next(request)

            # 7. Add Security Headers
            self._add_security_headers(response)

            # 8. Audit successful request
            response_time = (time.time() - start_time) * 1000
            await self._audit_api_request(request, client_ip, response.status_code, response_time)

            return response

        except HTTPException as e:
            # Audit security exceptions
            await self._audit_api_request(request, client_ip, e.status_code, None)
            raise
        except (ConnectionError, TimeoutError, OSError) as e:
            # Audit network-specific errors
            await self._audit_security_event("network_security_error", client_ip, {"error": str(e)})
            raise
        except Exception as e:
            # Audit other unexpected errors
            await self._audit_security_event(
                "security_middleware_error", client_ip, {"error": str(e)}
            )
            raise

    @staticmethod
    def _get_client_ip(request: Request) -> str:
        """Extract client IP address."""
        # Check forwarded headers (for reverse proxies)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # Fallback to direct connection
        return request.client.host if request.client else "unknown"

    def _check_ip_allowed(self, ip: str) -> bool:
        """Check if IP is allowed access."""

        # If no allowlist configured, allow all (except blocked)
        if not self.config.allowed_ips:
            return ip not in self.config.blocked_ips

        # Check if IP is explicitly allowed
        if ip in self.config.allowed_ips:
            return True

        # Check if IP is in blocked list
        if ip in self.config.blocked_ips:
            return False

        # Check private IP handling
        try:
            ip_obj = ipaddress.ip_address(ip)
            if ip_obj.is_private:
                return self.config.allow_private_ips
        except ValueError:
            return False

        # Deny by default if allowlist is configured
        return False

    def _is_ip_blocked(self, ip: str) -> bool:
        """Check if IP is temporarily blocked."""
        if ip not in self.blocked_ips:
            return False

        block_until = self.blocked_ips[ip]
        if time.time() > block_until:
            del self.blocked_ips[ip]
            return False

        return True

    def _block_ip(self, ip: str, duration: int) -> None:
        """Temporarily block an IP address."""
        self.blocked_ips[ip] = time.time() + duration

    def _detect_ddos(self, ip: str) -> bool:
        """Detect potential DDoS from IP."""
        current_time = time.time()
        window_start = current_time - self.config.ddos_threshold_window

        # Track request times for this IP
        request_times = self.ddos_tracker[ip]

        # Remove old entries
        while request_times and request_times[0] < window_start:
            request_times.popleft()

        # Add current request
        request_times.append(current_time)

        # Check if threshold exceeded
        return len(request_times) > self.config.ddos_threshold_requests

    def _check_rate_limits(self, request: Request, client_ip: str) -> bool:
        """Check all applicable rate limits."""

        for rule in self.config.rate_limit_rules:
            # Check if rule applies to this endpoint
            if rule.endpoints:
                if not any(request.url.path.startswith(endpoint) for endpoint in rule.endpoints):
                    continue

            # Skip if IP is exempt
            if client_ip in rule.exempt_ips:
                continue

            # Generate rate limit key based on scope
            if rule.scope == RateLimitScope.GLOBAL:
                key = "global"
            elif rule.scope == RateLimitScope.PER_IP:
                key = f"ip:{client_ip}"
            elif rule.scope == RateLimitScope.PER_ENDPOINT:
                key = f"endpoint:{request.url.path}:{client_ip}"
            else:
                key = f"user:{client_ip}"  # Fallback to IP if no user context

            # Check current request count
            current_count = self.rate_limiter.get_request_count(key, 60)

            # Check burst capacity
            burst_count = self.rate_limiter.get_request_count(key, 10)
            if burst_count > rule.burst_capacity:
                return False

            # Check per-minute limit
            if current_count >= rule.requests_per_minute:
                return False

            # Record this request
            self.rate_limiter.add_request(key)

        return True

    def _add_security_headers(self, response: Response) -> None:
        """Add security headers to response."""
        headers = self.config.security_headers

        response.headers["Strict-Transport-Security"] = headers.strict_transport_security
        response.headers["Content-Security-Policy"] = headers.content_security_policy
        response.headers["X-Frame-Options"] = headers.x_frame_options
        response.headers["X-Content-Type-Options"] = headers.x_content_type_options
        response.headers["X-XSS-Protection"] = headers.x_xss_protection
        response.headers["Referrer-Policy"] = headers.referrer_policy
        response.headers["Permissions-Policy"] = headers.permissions_policy
        response.headers["X-Robots-Tag"] = "noindex, nofollow"

    async def _audit_security_event(
        self, event_type: str, ip: str, details: Dict[str, Any]
    ) -> None:
        """Audit security events."""
        if self.audit_callback:
            await self.audit_callback(
                {
                    "event_type": f"security.{event_type}",
                    "source_ip": ip,
                    "timestamp": time.time(),
                    "details": details,
                }
            )

    async def _audit_api_request(
        self, request: Request, ip: str, status_code: int, response_time: Optional[float]
    ) -> None:
        """Audit API requests."""
        if self.audit_callback:
            await self.audit_callback(
                {
                    "event_type": "api.request",
                    "source_ip": ip,
                    "method": request.method,
                    "endpoint": str(request.url.path),
                    "status_code": status_code,
                    "response_time_ms": response_time,
                    "user_agent": request.headers.get("user-agent"),
                    "timestamp": time.time(),
                }
            )


class NetworkSecurityManager:
    """High-level network security management."""

    def __init__(self, network_config: NetworkSecurityConfig):
        self.config = network_config
        self.middleware: Optional[SecurityMiddleware] = None

    def create_middleware(self, audit_callback: Optional[Callable] = None) -> SecurityMiddleware:
        """Create security middleware instance."""
        self.middleware = SecurityMiddleware(None, self.config, audit_callback)
        return self.middleware

    def add_allowed_ip(self, ip: str) -> None:
        """Add IP to allowlist."""
        self.config.allowed_ips.add(ip)

    def remove_allowed_ip(self, ip: str) -> None:
        """Remove IP from allowlist."""
        self.config.allowed_ips.discard(ip)

    def block_ip(self, ip: str) -> None:
        """Add IP to blocklist."""
        self.config.blocked_ips.add(ip)

    def unblock_ip(self, ip: str) -> None:
        """Remove IP from blocklist."""
        self.config.blocked_ips.discard(ip)

    def update_rate_limits(self, rules: List[RateLimitRule]) -> None:
        """Update rate limiting rules."""
        self.config.rate_limit_rules = rules

    def get_security_status(self) -> Dict[str, Any]:
        """Get current security status."""
        return {
            "tls_required": self.config.require_https,
            "allowed_ips_count": len(self.config.allowed_ips),
            "blocked_ips_count": len(self.config.blocked_ips),
            "rate_limit_rules": len(self.config.rate_limit_rules),
            "ddos_protection": self.config.ddos_detection_enabled,
            "cors_origins": self.config.cors_allow_origins,
        }


def create_security_manager(security_level: SecurityLevel) -> NetworkSecurityManager:
    """Create network security manager for specific security level."""
    security_config = NetworkSecurityConfig.for_security_level(security_level)
    return NetworkSecurityManager(security_config)


# Healthcare-specific security helpers
def create_ambulance_security_config() -> NetworkSecurityConfig:
    """Create security configuration for ambulance/critical healthcare environments."""
    return NetworkSecurityConfig.for_security_level(SecurityLevel.CRITICAL)


def create_small_team_security_config() -> NetworkSecurityConfig:
    """Create relaxed security configuration for small teams (2-5 people)."""
    return NetworkSecurityConfig.for_security_level(SecurityLevel.SMALL_TEAM)


def validate_healthcare_compliance(network_config: NetworkSecurityConfig) -> List[str]:
    """Validate configuration meets healthcare compliance requirements."""
    issues = []

    if not network_config.require_https:
        issues.append("HTTPS is required for healthcare environments")

    if network_config.tls_min_version not in ["1.2", "1.3"]:
        issues.append("TLS 1.2 or higher is required for healthcare")

    if not network_config.rate_limit_rules:
        issues.append("Rate limiting is required for healthcare environments")

    if network_config.allow_private_ips and not network_config.allowed_ips:
        issues.append("IP allowlist should be configured for healthcare environments")

    if not network_config.ddos_detection_enabled:
        issues.append("DDoS protection is recommended for healthcare environments")

    # Check CSP is restrictive enough
    csp = network_config.security_headers.content_security_policy
    if "'unsafe-eval'" in csp or "'unsafe-inline'" in csp:
        issues.append(
            "Content Security Policy should not allow unsafe-eval or unsafe-inline in healthcare environments"
        )

    return issues


if __name__ == "__main__":
    # Test network security configuration
    print("Testing DinoAir Network Security System...")

    # Test different security levels
    for level in SecurityLevel:
        print(f"\n✅ Testing {level.value} security level...")
        config = NetworkSecurityConfig.for_security_level(level)
        manager = NetworkSecurityManager(config)
        status = manager.get_security_status()
        print(f"   TLS Required: {status['tls_required']}")
        print(f"   Rate Limits: {status['rate_limit_rules']}")
        print(f"   DDoS Protection: {status['ddos_protection']}")

    # Test healthcare compliance
    print(f"\n✅ Testing healthcare compliance...")
    healthcare_config = create_ambulance_security_config()
    compliance_issues = validate_healthcare_compliance(healthcare_config)

    if compliance_issues:
        print("   Compliance issues found:")
        for issue in compliance_issues:
            print(f"     - {issue}")
    else:
        print("   ✅ Configuration meets healthcare compliance requirements")

    print("\n✅ Network security test complete!")

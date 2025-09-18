"""
Comprehensive tests for the versioned configuration system
Tests schema validation, precedence, environment overrides, and compatibility
"""

import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

import pytest

from config.compatibility import CompatibilityConfigLoader, get_legacy_defaults
from config.versioned_config import (
    ConfigSource,
    ConfigurationError,
    ConfigValue,
    VersionedConfigManager,
)


sys.path.insert(0, str(Path(__file__).parent.parent))


class TestConfigSource(unittest.TestCase):
    """Test ConfigSource dataclass"""

    def test_config_source_creation(self):
        """Test ConfigSource creation with different parameters"""
        # Basic source
        source = ConfigSource("test")
        assert source.name == "test"
        assert source.path is None
        assert source.data == {}
        assert source.priority == 0
        assert not source.loaded
        assert source.error is None

        # Source with path
        path = Path("/test/path")
        source = ConfigSource("test", path, {"key": "value"}, 5)
        assert source.path == path
        assert source.data == {"key": "value"}
        assert source.priority == 5


class TestConfigValue(unittest.TestCase):
    """Test ConfigValue dataclass"""

    def test_config_value_creation(self):
        """Test ConfigValue creation"""
        value = ConfigValue(
            value="test_value",
            source="file",
            path="app.name",
            env_var="APP_NAME",
            default="default_value",
            schema_type="string",
        )

        assert value.value == "test_value"
        assert value.source == "file"
        assert value.path == "app.name"
        assert value.env_var == "APP_NAME"
        assert value.default == "default_value"
        assert value.schema_type == "string"


class TestVersionedConfigManager(unittest.TestCase):
    """Test the VersionedConfigManager class"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

        # Create test schema
        self.test_schema = {
            "schema_version": "1.0.0",
            "type": "object",
            "properties": {
                "app": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "default": "Test App", "env_var": "APP_NAME"},
                        "debug": {"type": "boolean", "default": False, "env_var": "DEBUG"},
                        "port": {
                            "type": "integer",
                            "default": 8080,
                            "env_var": "PORT",
                            "minimum": 1,
                            "maximum": 65535,
                        },
                    },
                },
                "database": {
                    "type": "object",
                    "properties": {
                        "timeout": {
                            "type": "integer",
                            "default": 30,
                            "env_var": "DB_TIMEOUT",
                            "minimum": 1,
                        }
                    },
                },
            },
        }

        # Create test files
        self.schema_path = self.temp_path / "schema.json"
        self.config_path = self.temp_path / "config.json"
        self.env_path = self.temp_path / ".env"

        with open(self.schema_path, "w") as f:
            json.dump(self.test_schema, f)

    def tearDown(self):
        """Clean up test fixtures"""
        import shutil

        shutil.rmtree(self.temp_dir)

        # Clean up environment variables
        test_env_vars = ["APP_NAME", "DEBUG", "PORT", "DB_TIMEOUT"]
        for var in test_env_vars:
            if var in os.environ:
                del os.environ[var]

    def test_schema_loading(self):
        """Test schema loading and parsing"""
        config = VersionedConfigManager(
            schema_path=self.schema_path,
            config_file_path=self.config_path,
            env_file_path=self.env_path,
            validate_on_load=False,
        )

        assert config.get_schema_version() == "1.0.0"
        assert len(config.env_mappings) == 4
        assert "APP_NAME" in config.env_mappings
        assert config.env_mappings["APP_NAME"] == "app.name"

    def test_missing_schema_error(self):
        """Test error handling for missing schema"""
        with pytest.raises(ConfigurationError):
            VersionedConfigManager(
                schema_path=self.temp_path / "nonexistent.json", validate_on_load=False
            )

    def test_defaults_extraction(self):
        """Test extraction of default values from schema"""
        config = VersionedConfigManager(
            schema_path=self.schema_path,
            config_file_path=self.config_path,
            env_file_path=self.env_path,
            validate_on_load=False,
        )

        assert config.get("app.name") == "Test App"
        assert not config.get("app.debug")
        assert config.get("app.port") == 8080
        assert config.get("database.timeout") == 30

    def test_file_config_override(self):
        """Test file configuration overriding defaults"""
        # Create config file
        file_config = {"app": {"name": "File App", "debug": True}, "database": {"timeout": 60}}

        with open(self.config_path, "w") as f:
            json.dump(file_config, f)

        config = VersionedConfigManager(
            schema_path=self.schema_path,
            config_file_path=self.config_path,
            env_file_path=self.env_path,
            validate_on_load=False,
        )

        assert config.get("app.name") == "File App"
        assert config.get("app.debug")
        assert config.get("app.port") == 8080  # Still default
        assert config.get("database.timeout") == 60

    def test_environment_override(self):
        """Test environment variables overriding file and defaults"""
        # Create config file
        file_config = {"app": {"name": "File App", "debug": True}}

        with open(self.config_path, "w") as f:
            json.dump(file_config, f)

        # Set environment variables
        os.environ["APP_NAME"] = "Env App"
        os.environ["PORT"] = "9000"

        config = VersionedConfigManager(
            schema_path=self.schema_path,
            config_file_path=self.config_path,
            env_file_path=self.env_path,
            validate_on_load=False,
        )

        assert config.get("app.name") == "Env App"  # From env
        assert config.get("app.debug")  # From file
        assert config.get("app.port") == 9000  # From env (converted to int)

    def test_env_file_override(self):
        """Test .env file overriding other sources"""
        # Create .env file
        env_content = """
        APP_NAME=DotEnv App
        DEBUG=false
        PORT=7000
        DB_TIMEOUT=120
        """

        with open(self.env_path, "w") as f:
            f.write(env_content)

        config = VersionedConfigManager(
            schema_path=self.schema_path,
            config_file_path=self.config_path,
            env_file_path=self.env_path,
            validate_on_load=False,
        )

        assert config.get("app.name") == "DotEnv App"
        assert not config.get("app.debug")
        assert config.get("app.port") == 7000
        assert config.get("database.timeout") == 120

    def test_precedence_order(self):
        """Test complete precedence: env > env_file > file > defaults"""
        # Create config file
        file_config = {"app": {"name": "File App", "debug": True, "port": 5000}}
        with open(self.config_path, "w") as f:
            json.dump(file_config, f)

        # Create .env file
        with open(self.env_path, "w") as f:
            f.write("APP_NAME=DotEnv App\nPORT=6000\n")

        # Set environment variable (highest priority)
        os.environ["APP_NAME"] = "System Env App"

        config = VersionedConfigManager(
            schema_path=self.schema_path,
            config_file_path=self.config_path,
            env_file_path=self.env_path,
            validate_on_load=False,
        )

        # System env wins for app.name
        assert config.get("app.name") == "System Env App"
        # .env file wins for port
        assert config.get("app.port") == 6000
        # File wins for debug (not overridden)
        assert config.get("app.debug")
        # Default wins for database.timeout
        assert config.get("database.timeout") == 30

    def test_type_conversion(self):
        """Test environment variable type conversion"""
        os.environ["DEBUG"] = "true"
        os.environ["PORT"] = "8080"
        os.environ["DB_TIMEOUT"] = "45"

        config = VersionedConfigManager(
            schema_path=self.schema_path,
            config_file_path=self.config_path,
            env_file_path=self.env_path,
            validate_on_load=False,
        )

        assert isinstance(config.get("app.debug"), bool)
        assert config.get("app.debug")

        assert isinstance(config.get("app.port"), int)
        assert config.get("app.port") == 8080

        assert isinstance(config.get("database.timeout"), int)
        assert config.get("database.timeout") == 45

    def test_get_with_source(self):
        """Test getting configuration values with source information"""
        # Set up different sources
        file_config = {"app": {"debug": True}}
        with open(self.config_path, "w") as f:
            json.dump(file_config, f)

        os.environ["APP_NAME"] = "Env App"

        config = VersionedConfigManager(
            schema_path=self.schema_path,
            config_file_path=self.config_path,
            env_file_path=self.env_path,
            validate_on_load=False,
        )

        # Test value from environment
        name_value = config.get_with_source("app.name")
        assert name_value.value == "Env App"
        assert name_value.source == "environment"
        assert name_value.env_var == "APP_NAME"

        # Test value from file
        debug_value = config.get_with_source("app.debug")
        assert debug_value.value
        assert debug_value.source == "file"

        # Test value from defaults
        port_value = config.get_with_source("app.port")
        assert port_value.value == 8080
        assert port_value.source == "defaults"

    def test_set_and_save(self):
        """Test setting values and saving configuration"""
        config = VersionedConfigManager(
            schema_path=self.schema_path,
            config_file_path=self.config_path,
            env_file_path=self.env_path,
            validate_on_load=False,
        )

        # Set a value
        config.set("app.name", "New App Name")
        assert config.get("app.name") == "New App Name"

        # Save configuration
        config.save_config_file()

        # Verify it was saved
        assert self.config_path.exists()
        with open(self.config_path) as f:
            json.load(f)

        # Note: Only non-default values should be saved
        # Implementation may vary based on exact save behavior


class TestCompatibilityConfigLoader(unittest.TestCase):
    """Test the compatibility layer"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

        # Create minimal schema for testing
        test_schema = {
            "schema_version": "1.0.0",
            "type": "object",
            "properties": {
                "app": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "default": "Test App"},
                        "debug": {"type": "boolean", "default": False},
                    },
                }
            },
        }

        schema_path = self.temp_path / "schema.json"
        with open(schema_path, "w") as f:
            json.dump(test_schema, f)

    def tearDown(self):
        """Clean up test fixtures"""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_backward_compatibility(self):
        """Test that CompatibilityConfigLoader provides old interface"""
        loader = CompatibilityConfigLoader()

        # Test get method
        app_name = loader.get("app.name", "default")
        assert isinstance(app_name, str)

        # Test set method
        loader.set("app.debug", True, save=False)
        assert loader.get("app.debug")

        # Test async compatibility methods
        assert isinstance(loader.is_async_enabled(), bool)
        assert isinstance(loader.should_use_async_file_ops(), bool)
        assert isinstance(loader.get_async_concurrent_limit(), int)


class TestLegacyDefaults(unittest.TestCase):
    """Test legacy DEFAULT_CONFIG compatibility"""

    def test_legacy_defaults_structure(self):
        """Test that legacy defaults maintain expected structure"""
        defaults = get_legacy_defaults()

        # Check expected keys
        expected_keys = [
            "APP_NAME",
            "VERSION",
            "DATABASE_TIMEOUT",
            "MAX_RETRIES",
            "BACKUP_RETENTION_DAYS",
            "SESSION_TIMEOUT",
            "MAX_NOTE_SIZE",
            "SUPPORTED_FILE_TYPES",
            "AI_MAX_TOKENS",
            "UI_UPDATE_INTERVAL",
        ]

        for key in expected_keys:
            assert key in defaults

        # Check types
        assert isinstance(defaults["APP_NAME"], str)
        assert isinstance(defaults["DATABASE_TIMEOUT"], int)
        assert isinstance(defaults["SUPPORTED_FILE_TYPES"], list)


class TestEnvironmentParsing(unittest.TestCase):
    """Test environment variable parsing"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

        # Create test schema
        test_schema = {
            "schema_version": "1.0.0",
            "type": "object",
            "properties": {
                "test": {
                    "type": "object",
                    "properties": {
                        "boolean_val": {"type": "boolean", "env_var": "TEST_BOOL"},
                        "integer_val": {"type": "integer", "env_var": "TEST_INT"},
                        "number_val": {"type": "number", "env_var": "TEST_FLOAT"},
                        "string_val": {"type": "string", "env_var": "TEST_STRING"},
                        "array_val": {"type": "array", "env_var": "TEST_ARRAY"},
                    },
                }
            },
        }

        schema_path = self.temp_path / "schema.json"
        with open(schema_path, "w") as f:
            json.dump(test_schema, f)

        self.schema_path = schema_path
        self.config_path = self.temp_path / "config.json"
        self.env_path = self.temp_path / ".env"

    def tearDown(self):
        """Clean up test fixtures"""
        import shutil

        shutil.rmtree(self.temp_dir)

        # Clean up environment
        test_vars = ["TEST_BOOL", "TEST_INT", "TEST_FLOAT", "TEST_STRING", "TEST_ARRAY"]
        for var in test_vars:
            if var in os.environ:
                del os.environ[var]

    def test_boolean_conversion(self):
        """Test boolean environment variable conversion"""
        test_cases = [
            ("true", True),
            ("false", False),
            ("1", True),
            ("0", False),
            ("yes", True),
            ("no", False),
            ("on", True),
            ("off", False),
            ("TRUE", True),
            ("FALSE", False),
        ]

        for env_value, expected in test_cases:
            os.environ["TEST_BOOL"] = env_value

            config = VersionedConfigManager(
                schema_path=self.schema_path,
                config_file_path=self.config_path,
                env_file_path=self.env_path,
                validate_on_load=False,
            )

            result = config.get("test.boolean_val")
            assert result == expected, f"Failed for {env_value}"

            del os.environ["TEST_BOOL"]

    def test_numeric_conversion(self):
        """Test numeric environment variable conversion"""
        # Integer conversion
        os.environ["TEST_INT"] = "42"

        # Float conversion
        os.environ["TEST_FLOAT"] = "3.14"

        config = VersionedConfigManager(
            schema_path=self.schema_path,
            config_file_path=self.config_path,
            env_file_path=self.env_path,
            validate_on_load=False,
        )

        assert config.get("test.integer_val") == 42
        assert isinstance(config.get("test.integer_val"), int)

        assert config.get("test.number_val") == 3.14
        assert isinstance(config.get("test.number_val"), float)


def run_tests():
    """Run all configuration tests"""

    # Create test suite
    test_suite = unittest.TestSuite()

    # Add test classes
    test_classes = [
        TestConfigSource,
        TestConfigValue,
        TestVersionedConfigManager,
        TestCompatibilityConfigLoader,
        TestLegacyDefaults,
        TestEnvironmentParsing,
    ]

    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)

    # Print results

    if result.failures:
        pass

    if result.errors:
        pass

    success = len(result.failures) == 0 and len(result.errors) == 0

    if success:
        pass
    else:
        pass

    return success


if __name__ == "__main__":
    sys.exit(0 if run_tests() else 1)

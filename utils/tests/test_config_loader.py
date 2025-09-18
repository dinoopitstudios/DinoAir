"""
Unit tests for config_loader.py module.
Tests configuration loading, environment variable handling, and config operations.
"""

import json
import os
from pathlib import Path
import tempfile
from unittest.mock import patch

from ..config_loader import ConfigLoader, load_env_file


class TestLoadEnvFile:
    """Test cases for load_env_file function."""

    def test_load_env_file_success(self):
        """Test successful loading of .env file."""
        env_content = """# Comment
DEBUG=true
LOG_LEVEL=INFO
DB_TIMEOUT=30
EMPTY_VAR=
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write(env_content)
            f.flush()

            try:
                result = load_env_file(Path(f.name))
                expected = {
                    "DEBUG": "true",
                    "LOG_LEVEL": "INFO",
                    "DB_TIMEOUT": "30",
                    "EMPTY_VAR": "",
                }
                assert result == expected
            finally:
                f.close()  # Explicitly close file handle on Windows
                os.unlink(f.name)

    def test_load_env_file_not_exists(self):
        """Test loading non-existent .env file."""
        result = load_env_file(Path("/nonexistent/.env"))
        assert result == {}

    def test_load_env_file_empty(self):
        """Test loading empty .env file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("")
            f.flush()

            try:
                result = load_env_file(Path(f.name))
                assert result == {}
            finally:
                f.close()  # Explicitly close file handle on Windows
                os.unlink(f.name)

    def test_load_env_file_malformed(self):
        """Test loading .env file with malformed lines."""
        env_content = """VALID=value
INVALID_LINE
ANOTHER=valid
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write(env_content)
            f.flush()

            try:
                result = load_env_file(Path(f.name))
                expected = {"VALID": "value", "ANOTHER": "valid"}
                assert result == expected
            finally:
                f.close()  # Explicitly close file handle on Windows
                os.unlink(f.name)


class TestConfigLoader:
    """Test cases for ConfigLoader class."""

    def test_init_with_config_path(self):
        """Test initialization with custom config path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.json"
            loader = ConfigLoader(config_path)

            assert loader.config_path == config_path
            assert loader.env_path == Path(temp_dir) / ".env"

    def test_load_config_file_exists(self):
        """Test loading configuration when file exists."""
        config_data = {
            "app": {"name": "TestApp", "version": "1.0.0"},
            "database": {"host": "localhost"},
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            with open(config_path, "w") as f:
                json.dump(config_data, f)

            with patch("utils.config_loader.load_env_file", return_value={}):
                loader = ConfigLoader(config_path)
                # Config should merge file data with defaults
                assert loader.config_data["app"]["name"] == "TestApp"  # From config file
                assert loader.config_data["app"]["version"] == "1.0.0"  # From config file
                assert loader.config_data["database"]["host"] == "localhost"  # From config file
                assert loader.config_data["app"]["theme"] == "light"  # From defaults
                assert loader.config_data["ai"]["model"] == "gpt-3.5-turbo"  # From defaults

    def test_load_config_file_not_exists(self):
        """Test loading configuration when file doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "nonexistent.json"

            with patch("utils.config_loader.load_env_file", return_value={}):
                loader = ConfigLoader(config_path)
                # Should create default config
                assert "app" in loader.config_data
                assert "database" in loader.config_data

    def test_env_overrides(self):
        """Test environment variable overrides."""
        config_data = {
            "app": {"debug": False},
            "logging": {"level": "WARNING"},
            "database": {"connection_timeout": 10},
        }

        env_vars = {"DEBUG": "true", "LOG_LEVEL": "INFO", "DB_TIMEOUT": "30"}

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            with open(config_path, "w") as f:
                json.dump(config_data, f)

            with patch("utils.config_loader.load_env_file", return_value=env_vars):
                loader = ConfigLoader(config_path)

                # Check that env vars overrode config
                assert loader.get("app.debug") is True
                assert loader.get("logging.level") == "INFO"
                assert loader.get("database.connection_timeout") == 30

    def test_env_type_conversion(self):
        """Test environment variable type conversion."""
        env_vars = {
            "DEBUG": "true",
            "LOG_LEVEL": "INFO",
            "DB_TIMEOUT": "30",
            "TEMPERATURE": "0.7",
            "MAX_TOKENS": "2000",
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            with open(config_path, "w") as f:
                json.dump({}, f)

            with patch("utils.config_loader.load_env_file", return_value=env_vars):
                loader = ConfigLoader(config_path)

                assert loader.get("app.debug") is True  # bool
                assert loader.get("logging.level") == "INFO"  # string
                assert loader.get("database.connection_timeout") == 30  # int
                assert loader.get("ai.temperature") == 0.7  # float
                assert loader.get("ai.max_tokens") == 2000  # int

    def test_get_method(self):
        """Test get method with dot notation."""
        config_data = {
            "app": {"name": "TestApp", "settings": {"theme": "dark"}},
            "database": {"host": "localhost"},
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            with open(config_path, "w") as f:
                json.dump(config_data, f)

            with patch("utils.config_loader.load_env_file", return_value={}):
                loader = ConfigLoader(config_path)

                assert loader.get("app.name") == "TestApp"
                assert loader.get("app.settings.theme") == "dark"
                assert loader.get("database.host") == "localhost"
                assert loader.get("nonexistent.key", "default") == "default"
                assert loader.get("nonexistent.key") is None

    def test_get_env_method(self):
        """Test get_env method."""
        env_vars = {"API_KEY": "secret123", "DEBUG": "true"}

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"

            with patch("utils.config_loader.load_env_file", return_value=env_vars):
                loader = ConfigLoader(config_path)

                assert loader.get_env("API_KEY") == "secret123"
                assert loader.get_env("DEBUG") == "true"
                assert loader.get_env("NONEXISTENT", "default") == "default"
                assert loader.get_env("NONEXISTENT") == ""

    def test_set_method(self):
        """Test set method with dot notation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"

            with patch("utils.config_loader.load_env_file", return_value={}):
                loader = ConfigLoader(config_path)

                # Test setting new values
                loader.set("app.new_setting", "value")
                assert loader.get("app.new_setting") == "value"

                # Test updating existing values
                loader.set("app.name", "UpdatedApp")
                assert loader.get("app.name") == "UpdatedApp"

                # Test nested creation
                loader.set("new.section.deep.value", 42)
                assert loader.get("new.section.deep.value") == 42

    def test_save_config(self):
        """Test saving configuration to file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"

            with patch("utils.config_loader.load_env_file", return_value={}):
                loader = ConfigLoader(config_path)

                # Modify config
                loader.set("test.key", "test_value")

                # Save
                loader.save_config()

                # Verify file was written
                assert config_path.exists()
                with open(config_path) as f:
                    saved_data = json.load(f)
                    assert saved_data["test"]["key"] == "test_value"

    def test_create_default_config(self):
        """Test default configuration creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"

            with patch("utils.config_loader.load_env_file", return_value={}):
                loader = ConfigLoader(config_path)

                # Should have all expected sections
                assert "app" in loader.config_data
                assert "database" in loader.config_data
                assert "ai" in loader.config_data
                assert "ui" in loader.config_data
                assert "error_handling" in loader.config_data

                # Check some default values
                assert loader.get("app.name") == "DinoAir 2.0"
                assert loader.get("app.version") == "2.0.0"
                assert loader.get("database.backup_on_startup") is True
                assert loader.get("ai.model") == "gpt-3.5-turbo"

    def test_error_handling(self):
        """Test error handling in config loading."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "invalid.json"

            # Create invalid JSON
            with open(config_path, "w") as f:
                f.write("invalid json content")

            with patch("utils.config_loader.load_env_file", return_value={}):
                with patch("utils.config_loader.Logger") as mock_logger:
                    loader = ConfigLoader(config_path)

                    # Should have logged error
                    mock_logger().error.assert_called()

                    # Should have created default config
                    assert "app" in loader.config_data

    def test_save_config_error_handling(self):
        """Test error handling in config saving."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "readonly" / "config.json"

            with patch("utils.config_loader.load_env_file", return_value={}):
                loader = ConfigLoader(config_path)

                # Try to save without directory existing
                loader.save_config()

                # Should have logged error but not crashed
                # (Logger is mocked in other tests, but in real usage it would log)


class TestConfigLoaderIntegration:
    """Integration tests for ConfigLoader."""

    def test_full_workflow(self):
        """Test complete configuration workflow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            env_path = Path(temp_dir) / ".env"

            # Create initial config
            initial_config = {
                "app": {"name": "TestApp", "debug": False},
                "database": {"host": "localhost"},
            }
            with open(config_path, "w") as f:
                json.dump(initial_config, f)

            # Create .env file
            with open(env_path, "w") as f:
                f.write("DEBUG=true\nDB_HOST=testdb\n")

            loader = ConfigLoader(config_path)

            # Check that env overrode config
            assert loader.get("app.debug") is True
            assert loader.get("database.host") == "testdb"

            # Modify and save
            loader.set("app.version", "2.0.0")
            loader.save_config()

            # Verify persistence
            with open(config_path) as f:
                saved = json.load(f)
                assert saved["app"]["version"] == "2.0.0"
                assert saved["app"]["debug"] is True  # From env

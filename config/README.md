# DinoAir Versioned Configuration System

## Overview

The DinoAir application now uses a comprehensive versioned configuration system that provides:

- **Schema Validation** using JSON Schema (when jsonschema is available)
- **Clear Precedence**: Environment Variables > .env File > Config File > Defaults
- **Comprehensive Environment Variable Mapping** (61 mapped variables)
- **Type Conversion and Validation**
- **Backward Compatibility** with existing ConfigLoader interface
- **Source Tracking** for debugging configuration issues

## Files Structure

```
DinoAir3.0/
├── config/
│   ├── schema.json              # Versioned schema with validation rules
│   ├── app_config.json          # Default configuration file
│   ├── versioned_config.py      # Core configuration manager
│   ├── compatibility.py         # Backward compatibility layer
│   ├── demo_config.py          # Demonstration script
│   └── test_config.py          # Comprehensive test suite
├── .env                        # Environment variable overrides (gitignored)
└── .env.example               # Environment variable examples
```

## Quick Start

### Using the New System

```python
from config.versioned_config import get_config

# Get global configuration instance
config = get_config()

# Access configuration values
app_name = config.get("app.name")
debug_mode = config.get("app.debug")
db_timeout = config.get("database.connection_timeout")

# Get value with source information
debug_info = config.get_with_source("app.debug")
print(f"Debug mode: {debug_info.value} (from: {debug_info.source})")
```

### Backward Compatibility

Existing code using ConfigLoader continues to work:

```python
from utils.config_loader import ConfigLoader

# This now uses the new system under the hood
loader = ConfigLoader()
app_name = loader.get("app.name")
loader.set("app.debug", True)
```

## Configuration Schema

The schema defines 59 configuration settings across 11 categories:

- **app**: Core application settings (7 settings)
- **database**: Database configuration (7 settings)
- **ai**: AI and language model settings (3 settings)
- **lmstudio**: LM Studio integration (3 settings)
- **ui**: User interface settings (6 settings)
- **logging**: Logging configuration (4 settings)
- **async**: Asynchronous operations (9 settings)
- **input_processing**: Input validation (3 settings)
- **pseudocode_translator**: Translation settings (2 settings)
- **notes**: Notes system configuration (3 settings)
- **error_handling**: Error handling and resilience (12 settings)

## Environment Variable Mapping

Every configuration setting has a corresponding environment variable:

```bash
# App settings
DEBUG=true                      # app.debug
APP_THEME=dark                  # app.theme
APP_NAME="My DinoAir"          # app.name

# Database settings
DB_TIMEOUT=60                   # database.connection_timeout
DB_HOST=remote.example.com      # database.host

# AI settings
AI_MODEL=gpt-4                  # ai.model
AI_MAX_TOKENS=4000             # ai.max_tokens
AI_TEMPERATURE=0.3             # ai.temperature
```

## Configuration Precedence

Values are resolved in this order (highest to lowest priority):

1. **Environment Variables** (e.g., `DEBUG=true`)
2. **`.env` File** (e.g., `DEBUG=true` in .env)
3. **Config File** (e.g., `"debug": true` in app_config.json)
4. **Schema Defaults** (e.g., `"default": false` in schema.json)

## Validation

When jsonschema is available, all configuration is validated against the schema:

- **Type Validation**: Ensures values are correct types (string, boolean, integer, etc.)
- **Range Validation**: Enforces minimum/maximum values
- **Enum Validation**: Restricts values to allowed options
- **Format Validation**: Validates URLs, hostnames, etc.

## Testing and Validation

Run the comprehensive test suite:

```bash
cd DinoAir3.0
python3 config/test_config.py
```

Run the demonstration script:

```bash
python3 config/demo_config.py
```

## Migration from Old System

The new system is designed to be drop-in compatible:

1. **No code changes required** for basic usage
2. **ConfigLoader** class continues to work unchanged
3. **DEFAULT_CONFIG** dictionary is still available
4. **Environment variable mappings** are preserved and expanded

### Optional Migration Steps

1. **Install jsonschema** for full validation:

   ```bash
   pip install jsonschema
   ```

2. **Create .env file** from .env.example:

   ```bash
   cp .env.example .env
   # Edit .env with your custom settings
   ```

3. **Update configuration access** to use new features:
   ```python
   # New features available
   config = get_config()
   all_settings = config.list_all_settings()
   source_info = config.get_source_info()
   ```

## Benefits

### For Developers

- **Clear configuration source** - know exactly where each value comes from
- **Type safety** - automatic conversion and validation
- **Environment-specific overrides** - easy deployment configuration
- **Comprehensive testing** - 16 tests covering all scenarios

### For Operations

- **Environment variable control** - override any setting via env vars
- **Configuration validation** - catch configuration errors early
- **Source tracking** - debug configuration issues easily
- **Flexible deployment** - .env files for different environments

### For Maintenance

- **Versioned schema** - track configuration changes over time
- **Centralized defaults** - single source of truth for all settings
- **Backward compatibility** - gradual migration possible
- **Comprehensive documentation** - every setting documented with types and ranges

## Advanced Usage

### Custom Configuration Paths

```python
from config.versioned_config import VersionedConfigManager

config = VersionedConfigManager(
    schema_path=Path("custom/schema.json"),
    config_file_path=Path("custom/config.json"),
    env_file_path=Path("custom/.env")
)
```

### Validation Control

```python
# Disable validation for development
config = VersionedConfigManager(validate_on_load=False)

# Manual validation
try:
    config.validate()
except SchemaValidationError as e:
    print(f"Configuration invalid: {e}")
```

### Source Information

```python
# Get configuration source info
sources = config.get_source_info()
for source in sources:
    print(f"{source['name']}: {source['keys_count']} keys")

# Get environment mappings
mappings = config.get_env_mappings()
print(f"Total environment variables: {len(mappings)}")
```

## Schema Evolution

The schema is versioned (currently v1.0.0) to support future evolution:

- **Add new settings** without breaking existing code
- **Deprecate old settings** with proper migration paths
- **Update validation rules** while maintaining compatibility
- **Track configuration changes** across application versions

## Troubleshooting

### Common Issues

1. **jsonschema not available**: Install with `pip install jsonschema`
2. **Invalid environment variable**: Check type conversion rules
3. **Configuration not found**: Verify file paths and permissions
4. **Validation errors**: Check schema requirements and value ranges

### Debugging

```python
# Show all configuration sources
config = get_config()
for source in config.get_source_info():
    print(f"{source['name']}: loaded={source['loaded']}, error={source['error']}")

# Show where a value comes from
value_info = config.get_with_source("app.debug")
print(f"app.debug = {value_info.value} (from {value_info.source})")
```

This completes the DinoAir versioned configuration system implementation.

# User Guide

## Installation and Setup

### Requirements

- Python 3.8+
- SQLite 3.35+
- Cryptography library

### Installation

```bash
# Clone the repository
git clone https://github.com/Dinopitstudios/DinoAir.git
cd DinoAir

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Configure DinoAir using the `config/app_config.json` file or environment variables.

#### Database Configuration

```json
{
  "database": {
    "user_data_path": "/custom/path/to/data",
    "auto_cleanup_test_data": true,
    "max_backup_age_days": 30
  }
}
```

#### Artifacts Configuration

```json
{
  "artifacts": {
    "encryption_at_rest": true,
    "encryption_algorithm": "AES-256-CBC",
    "file_size_threshold": 1048576,
    "default_encryption_fields": ["content", "metadata"],
    "key_rotation_days": 90
  }
}
```

## Basic Usage

### Database Initialization

```python
from database.initialize_db import initialize_user_databases

# Initialize for default user
db_manager = initialize_user_databases()

# Initialize for specific user with custom path
db_manager = initialize_user_databases(
    user_name="john_doe",
    base_dir="/custom/data/path"
)
```

### Working with Artifacts

```python
from database.artifacts_db import ArtifactsDatabase
from models.artifact import Artifact

# Create artifacts database with encryption
artifacts_db = ArtifactsDatabase(
    db_manager,
    encryption_password="your_secure_password"
)

# Create an artifact
artifact = Artifact(
    name="Important Document",
    description="Confidential project document",
    content_type="application/pdf",
    project_id="project-123"
)

# Store with file content
with open("document.pdf", "rb") as f:
    content = f.read()

result = artifacts_db.create_artifact(artifact, content=content)
print(f"Artifact created: {result['success']}")

# Retrieve artifact content (automatically decrypted)
retrieved_content = artifacts_db.get_artifact_content(artifact.id)
```

### Data Cleanup

```python
from utils.dev_cleanup import UserDataCleanupManager

# Analyze current data usage
cleanup_manager = UserDataCleanupManager(verbose=True)
analysis = cleanup_manager.analyze_user_data()

# Perform cleanup
results = cleanup_manager.full_cleanup(
    max_age_hours=24,
    cleanup_repo=True
)
```

## Security Best Practices

### Encryption

1. **Use strong passwords** for encryption
2. **Rotate encryption keys** regularly
3. **Enable encryption-at-rest** for sensitive data
4. **Validate permissions** before storing data

### Data Management

1. **Store data outside repository** by default
2. **Use temporary directories** for tests
3. **Clean up old data** regularly
4. **Monitor disk usage** and storage paths

### Configuration Security

1. **Use environment variables** for sensitive configuration
2. **Restrict file permissions** on configuration files
3. **Validate configuration** before use
4. **Log security events** appropriately

## Troubleshooting

### Common Issues

#### Permission Errors

```bash
# Check directory permissions
ls -la /path/to/user/data

# Fix permissions
chmod 755 /path/to/user/data
```

#### Encryption Errors

```python
# Test encryption setup
from utils.artifact_encryption import ArtifactEncryption

encryption = ArtifactEncryption("test_password")
test_data = encryption.encrypt_data("test")
decrypted = encryption.decrypt_data(test_data)
print(f"Encryption test: {'PASS' if decrypted == b'test' else 'FAIL'}")
```

#### Database Issues

```python
# Test database connection
from database.initialize_db import DatabaseManager

db_manager = DatabaseManager()
try:
    with db_manager.get_notes_connection() as conn:
        print("Database connection: PASS")
except Exception as e:
    print(f"Database connection: FAIL - {e}")
```

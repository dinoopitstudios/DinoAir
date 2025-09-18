# API Reference

This section provides comprehensive API documentation for all DinoAir modules.

## Core Modules

```{toctree}
:maxdepth: 2

database
models
utils
config
```

## Database Module

```{eval-rst}
.. automodule:: database
   :members:
   :undoc-members:
   :show-inheritance:
```

### Database Initialization

```{eval-rst}
.. automodule:: database.initialize_db
   :members:
   :undoc-members:
   :show-inheritance:
```

### Artifacts Database

```{eval-rst}
.. automodule:: database.artifacts_db
   :members:
   :undoc-members:
   :show-inheritance:
```

### Notes Service

```{eval-rst}
.. automodule:: database.notes_service
   :members:
   :undoc-members:
   :show-inheritance:
```

## Models

```{eval-rst}
.. automodule:: models
   :members:
   :undoc-members:
   :show-inheritance:
```

### Artifact Model

```{eval-rst}
.. automodule:: models.artifact
   :members:
   :undoc-members:
   :show-inheritance:
```

### Note Model

```{eval-rst}
.. automodule:: models.note
   :members:
   :undoc-members:
   :show-inheritance:
```

## Utilities

```{eval-rst}
.. automodule:: utils
   :members:
   :undoc-members:
   :show-inheritance:
```

### Artifact Encryption

```{eval-rst}
.. automodule:: utils.artifact_encryption
   :members:
   :undoc-members:
   :show-inheritance:
```

### Performance Monitor

```{eval-rst}
.. automodule:: utils.performance_monitor
   :members:
   :undoc-members:
   :show-inheritance:
```

### Development Cleanup

```{eval-rst}
.. automodule:: utils.dev_cleanup
   :members:
   :undoc-members:
   :show-inheritance:
```

## Configuration

```{eval-rst}
.. automodule:: config
   :members:
   :undoc-members:
   :show-inheritance:
```

## Examples

### Basic Usage

```python
from database.initialize_db import DatabaseManager

# Initialize with default settings
db_manager = DatabaseManager()
db_manager.initialize_all_databases()

# Initialize with encryption
from database.artifacts_db import ArtifactsDatabase
artifacts_db = ArtifactsDatabase(db_manager, encryption_password="secure_password")
```

### Artifact Management

```python
from models.artifact import Artifact

# Create an artifact
artifact = Artifact(
    id="test-artifact",
    name="My Document",
    description="Important document",
    content_type="application/pdf"
)

# Store with encryption
result = artifacts_db.create_artifact(artifact, content=pdf_bytes)
```

### Encryption

```python
from utils.artifact_encryption import ArtifactEncryption

# Initialize encryption
encryption = ArtifactEncryption("your_password")

# Encrypt data
encrypted = encryption.encrypt_data("sensitive information")

# Decrypt data
decrypted = encryption.decrypt_data(encrypted)
```

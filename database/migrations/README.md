# DinoAir Database Migration System

## Overview

This document describes the new versioned migration system that replaces the ad-hoc PRAGMA checks in DinoAir's database management. The migration system provides proper tracking, versioning, and rollback capabilities for database schema changes.

## Architecture

### Core Components

1. **Migration Base Classes** (`database/migrations/base.py`)
   - `BaseMigration`: Abstract base class for all migrations
   - `MigrationRecord`: Represents applied migration records
   - `MigrationError`: Custom exception for migration failures
   - Utility functions for migration table management

2. **Migration Runner** (`database/migrations/runner.py`)
   - `MigrationRunner`: Manages execution of migrations
   - Supports dry-run mode, target versions, and rollbacks
   - Provides migration status and tracking

3. **Migration Loader** (`database/migrations/loader.py`)
   - Dynamically loads migration scripts from the scripts directory
   - Validates and instantiates migration classes
   - Provides convenient access to notes migrations

4. **Migration Scripts** (`database/migrations/scripts/`)
   - Individual migration files with version numbers
   - Each migration implements `up()` and optionally `down()` methods

## Migration Tracking

### Schema Migrations Table

A dedicated `schema_migrations` table tracks applied migrations:

```sql
CREATE TABLE schema_migrations (
    version TEXT NOT NULL,
    name TEXT NOT NULL,
    applied_at DATETIME NOT NULL,
    description TEXT DEFAULT '',
    checksum TEXT DEFAULT NULL,
    PRIMARY KEY (version, name)
);
```

### Migration Naming Convention

Migration files follow the pattern: `XXX_migration_name.py`

- `XXX`: Zero-padded version number (001, 002, etc.)
- `migration_name`: Descriptive name using underscores

## Current Migrations

### 001_add_notes_project_id.py

- **Purpose**: Add `project_id` column to notes table
- **Description**: Enables project association functionality
- **Replaces**: `DatabaseManager._apply_notes_project_id_migration()`

### 002_add_notes_is_deleted.py

- **Purpose**: Add `is_deleted` column to notes table
- **Description**: Enables soft delete functionality
- **Replaces**: Ad-hoc column addition in `NotesRepository._ensure_database_ready()`

### 003_add_notes_content_html.py

- **Purpose**: Add `content_html` column to notes table
- **Description**: Enables HTML content rendering
- **Replaces**: Ad-hoc column addition in `NotesRepository._ensure_database_ready()`

## Integration with DatabaseManager

### Updated Schema Setup Process

1. **Schema DDLs Applied First**: Base table structure created
2. **Migration System Executed**: Versioned migrations applied in order
3. **Fallback Protection**: If migration system fails, falls back to old migration method

### Key Changes

- `DatabaseManager._setup_schema()` now calls `_run_notes_migrations()`
- `_run_notes_migrations()` loads and executes all pending migrations
- Error handling ensures database initialization doesn't fail if migrations have issues
- `NotesRepository._ensure_database_ready()` simplified (schema handled by migrations)

## Usage Examples

### Creating a New Migration

```python
# database/migrations/scripts/004_add_new_column.py
import sqlite3
from database.migrations.base import BaseMigration, MigrationError

class AddNewColumnMigration(BaseMigration):
    def __init__(self):
        super().__init__(
            version="004",
            name="add_new_column",
            description="Add new_column to notes table"
        )

    def up(self, conn: sqlite3.Connection) -> None:
        cursor = conn.cursor()
        cursor.execute("ALTER TABLE note_list ADD COLUMN new_column TEXT")
        conn.commit()

    def down(self, conn: sqlite3.Connection) -> None:
        # SQLite doesn't support DROP COLUMN easily
        raise MigrationError("Rollback not supported for this migration")
```

### Running Migrations Programmatically

```python
from database.migrations import MigrationRunner, get_notes_migrations

# Load migrations and run them
migrations = get_notes_migrations()
runner = MigrationRunner("notes")
runner.register_migrations(migrations)

with get_database_connection() as conn:
    executed = runner.run_migrations(conn)
    print(f"Applied {len(executed)} migrations")
```

### Checking Migration Status

```python
status = runner.get_migration_status(conn)
print(f"Applied: {status['applied_count']}/{status['total_migrations']}")
print(f"Up to date: {status['is_up_to_date']}")
```

## Benefits

### Over Previous System

1. **Proper Versioning**: Migrations are executed in order with version tracking
2. **Idempotency**: Migrations only run once and are tracked
3. **Rollback Support**: Migrations can optionally implement rollback logic
4. **Better Testing**: Each migration can be tested independently
5. **Clear History**: Full audit trail of applied schema changes
6. **Error Handling**: Better error reporting and recovery

### Development Workflow

1. **Predictable**: New schema changes follow standard migration patterns
2. **Collaborative**: Multiple developers can work on schema changes without conflicts
3. **Deployable**: Migrations run automatically during database initialization
4. **Maintainable**: Clear separation of concerns between schema and data operations

## Backward Compatibility

- Old `_apply_notes_project_id_migration()` kept as fallback
- Existing databases are automatically migrated to the new system
- No data loss or corruption during the transition
- Tests updated to reflect new system while maintaining compatibility tests

## Testing

### Test Coverage

- Unit tests for migration base classes and runner
- Integration tests with DatabaseManager
- Migration loader functionality tests
- Error handling and fallback behavior tests

### Test Files

- `database/tests/test_migrations.py` - Core migration system tests
- `database/tests/test_migrations_integration.py` - DatabaseManager integration tests
- `database/tests/test_migration_simple.py` - Simple verification script
- `database/tests/test_migration_loader.py` - Migration loader tests
- `database/tests/test_database_manager_integration.py` - Full integration test

## Future Enhancements

### Potential Improvements

1. **Migration Generator**: CLI tool to create new migration files
2. **Schema Diffing**: Automatically generate migrations from schema changes
3. **Data Migrations**: Support for data transformation migrations
4. **Parallel Migrations**: Support for non-conflicting parallel migration execution
5. **Migration Validation**: Pre-flight checks for migration safety

### Migration System Extension

The system is designed to be extensible for other databases beyond notes:

```python
# For other databases
memory_migrations = load_migrations_from_directory(memory_migrations_dir)
memory_runner = MigrationRunner("memory")
memory_runner.register_migrations(memory_migrations)
```

## Conclusion

The new migration system provides a robust, scalable foundation for managing database schema changes in DinoAir. It replaces ad-hoc PRAGMA checks with a proper versioned system that supports tracking, rollbacks, and collaborative development while maintaining full backward compatibility.

"""
Database Initialization Script
Manages multiple SQLite databases for the DinoAir application with proper typing and error handling
Refactored to reduce duplication with centralized helpers and declarative schema registries.
"""

from __future__ import annotations

import logging
import os
import shutil
import sqlite3
import tempfile
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Final

# Migration system
from .migrations import MigrationRunner, get_notes_migrations

# External resilient connection wrapper (behavior preserved)
from .resilient_db import ResilientDB

if TYPE_CHECKING:
    from collections.abc import Callable

LOGGER = logging.getLogger(__name__)

# Canonical database filenames (stable iteration order preserved)
DB_FILES: Final[dict[str, str]] = {
    "notes": "notes.db",
    "memory": "memory.db",
    "user_tools": "user_tools.db",
    "chat_history": "chat_history.db",
    "appointments": "appointments.db",
    "artifacts": "artifacts.db",
    "file_search": "file_search.db",
    "projects": "projects.db",
    "timers": "timers.db",
}

# Declarative schema definitions (idempotent DDLs; names/types preserved)
SCHEMA_DDLS: Final[dict[str, list[str]]] = {
    "notes": [
        """
            CREATE TABLE IF NOT EXISTS note_list (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT,
                content_html TEXT,
                tags TEXT,
                project_id TEXT,
                is_deleted INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """,
        # Single-column indexes for basic filters
        "CREATE INDEX IF NOT EXISTS idx_notes_title ON note_list(title)",
        "CREATE INDEX IF NOT EXISTS idx_notes_tags ON note_list(tags)",
        "CREATE INDEX IF NOT EXISTS idx_notes_created ON note_list(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_notes_updated ON note_list(updated_at)",
        "CREATE INDEX IF NOT EXISTS idx_notes_project ON note_list(project_id)",
        "CREATE INDEX IF NOT EXISTS idx_notes_is_deleted ON note_list(is_deleted)",
        # Compound indexes for common query patterns
        # Most common: is_deleted + ordering by updated_at (get_all_notes, get_deleted_notes)
        "CREATE INDEX IF NOT EXISTS idx_notes_active_updated ON note_list(is_deleted, updated_at DESC)",
        # Search queries: is_deleted + title for title searches
        "CREATE INDEX IF NOT EXISTS idx_notes_active_title ON note_list(is_deleted, title)",
        # Tag queries: is_deleted + tags for tag searches and filtering
        "CREATE INDEX IF NOT EXISTS idx_notes_active_tags ON note_list(is_deleted, tags) WHERE tags IS NOT NULL",
        # Project queries: is_deleted + project_id + updated_at for project-specific lists
        "CREATE INDEX IF NOT EXISTS idx_notes_project_active ON note_list(is_deleted, project_id, updated_at DESC)",
        # Tag presence check: is_deleted + tags not null for notes with any tags
        "CREATE INDEX IF NOT EXISTS idx_notes_has_tags ON note_list(is_deleted) WHERE tags IS NOT NULL AND tags != '[]'",
        # Notes without project: is_deleted + updated_at for orphaned notes
        "CREATE INDEX IF NOT EXISTS idx_notes_no_project ON note_list(is_deleted, updated_at DESC) WHERE project_id IS NULL",
        # Search with project filter: is_deleted + project_id + title for filtered searches
        "CREATE INDEX IF NOT EXISTS idx_notes_project_title ON note_list(is_deleted, project_id, title)",
    ],
    "memory": [
        """
            CREATE TABLE IF NOT EXISTS session_data (
                key TEXT PRIMARY KEY,
                value TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                expires_at DATETIME
            )
        """,
        """
            CREATE TABLE IF NOT EXISTS recent_notes (
                note_id TEXT,
                accessed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (note_id)
            )
        """,
        """
            CREATE TABLE IF NOT EXISTS watchdog_metrics (
                id TEXT PRIMARY KEY,
                timestamp DATETIME NOT NULL,
                vram_used_mb REAL,
                vram_total_mb REAL,
                vram_percent REAL,
                cpu_percent REAL,
                ram_used_mb REAL,
                ram_percent REAL,
                process_count INTEGER,
                dinoair_processes INTEGER,
                uptime_seconds INTEGER
            )
        """,
        """
            CREATE INDEX IF NOT EXISTS idx_metrics_timestamp
            ON watchdog_metrics(timestamp DESC)
        """,
        """
            CREATE INDEX IF NOT EXISTS idx_metrics_vram
            ON watchdog_metrics(vram_percent)
        """,
        """
            CREATE INDEX IF NOT EXISTS idx_metrics_processes
            ON watchdog_metrics(dinoair_processes)
        """,
    ],
    "user_tools": [
        """
            CREATE TABLE IF NOT EXISTS user_preferences (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """,
        """
            CREATE TABLE IF NOT EXISTS app_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level TEXT,
                message TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """,
    ],
    "chat_history": [
        """
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                project_id TEXT,
                task_id TEXT,
                tags TEXT,
                summary TEXT,
                status TEXT DEFAULT 'active'
            )
        """,
        """
            CREATE TABLE IF NOT EXISTS chat_messages (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                message TEXT NOT NULL,
                is_user BOOLEAN DEFAULT 1,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT,
                FOREIGN KEY (session_id) REFERENCES chat_sessions (id)
            )
        """,
        """
            CREATE TABLE IF NOT EXISTS chat_schedules (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                cron_expression TEXT NOT NULL,
                next_run DATETIME,
                last_run DATETIME,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (session_id) REFERENCES chat_sessions (id)
            )
        """,
        "CREATE INDEX IF NOT EXISTS idx_sessions_created ON chat_sessions(created_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_sessions_project ON chat_sessions(project_id)",
        "CREATE INDEX IF NOT EXISTS idx_sessions_task ON chat_sessions(task_id)",
        "CREATE INDEX IF NOT EXISTS idx_sessions_status ON chat_sessions(status)",
        "CREATE INDEX IF NOT EXISTS idx_messages_session ON chat_messages(session_id)",
        "CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON chat_messages(timestamp)",
        "CREATE INDEX IF NOT EXISTS idx_schedules_session ON chat_schedules(session_id)",
        "CREATE INDEX IF NOT EXISTS idx_schedules_next_run ON chat_schedules(next_run)",
    ],
    "appointments": [
        """
            CREATE TABLE IF NOT EXISTS calendar_events (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                event_type TEXT DEFAULT 'appointment',
                status TEXT DEFAULT 'scheduled',
                event_date DATE,
                start_time TIME,
                end_time TIME,
                all_day BOOLEAN DEFAULT 0,
                location TEXT,
                participants TEXT,
                project_id TEXT,
                chat_session_id TEXT,
                recurrence_pattern TEXT DEFAULT 'none',
                recurrence_rule TEXT,
                reminder_minutes_before INTEGER,
                reminder_sent BOOLEAN DEFAULT 0,
                tags TEXT,
                notes TEXT,
                color TEXT,
                metadata TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                completed_at DATETIME
            )
        """,
        """
            CREATE TABLE IF NOT EXISTS event_reminders (
                id TEXT PRIMARY KEY,
                event_id TEXT NOT NULL,
                reminder_time DATETIME NOT NULL,
                sent BOOLEAN DEFAULT 0,
                sent_at DATETIME,
                FOREIGN KEY (event_id) REFERENCES calendar_events (id)
            )
        """,
        """
            CREATE TABLE IF NOT EXISTS event_attachments (
                id TEXT PRIMARY KEY,
                event_id TEXT NOT NULL,
                file_name TEXT NOT NULL,
                file_path TEXT,
                file_type TEXT,
                file_size INTEGER,
                uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (event_id) REFERENCES calendar_events (id)
            )
        """,
        "CREATE INDEX IF NOT EXISTS idx_events_date ON calendar_events(event_date)",
        "CREATE INDEX IF NOT EXISTS idx_events_status ON calendar_events(status)",
        "CREATE INDEX IF NOT EXISTS idx_events_project ON calendar_events(project_id)",
        "CREATE INDEX IF NOT EXISTS idx_events_chat_session ON calendar_events(chat_session_id)",
        "CREATE INDEX IF NOT EXISTS idx_events_created ON calendar_events(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_reminders_event ON event_reminders(event_id)",
        "CREATE INDEX IF NOT EXISTS idx_reminders_time ON event_reminders(reminder_time)",
        "CREATE INDEX IF NOT EXISTS idx_attachments_event ON event_attachments(event_id)",
    ],
    "artifacts": [
        """
            CREATE TABLE IF NOT EXISTS artifacts (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                content_type TEXT DEFAULT 'text',
                status TEXT DEFAULT 'active',
                content TEXT,
                content_path TEXT,
                size_bytes INTEGER DEFAULT 0,
                mime_type TEXT,
                checksum TEXT,
                collection_id TEXT,
                parent_id TEXT,
                version INTEGER DEFAULT 1,
                is_latest BOOLEAN DEFAULT 1,
                encrypted_fields TEXT,
                encryption_key_id TEXT,
                project_id TEXT,
                chat_session_id TEXT,
                note_id TEXT,
                tags TEXT,
                metadata TEXT,
                properties TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                accessed_at DATETIME,
                FOREIGN KEY (collection_id) REFERENCES artifact_collections (id),
                FOREIGN KEY (parent_id) REFERENCES artifacts (id)
            )
        """,
        """
            CREATE TABLE IF NOT EXISTS artifact_versions (
                id TEXT PRIMARY KEY,
                artifact_id TEXT NOT NULL,
                version_number INTEGER NOT NULL,
                artifact_data TEXT NOT NULL,
                change_summary TEXT,
                changed_by TEXT,
                changed_fields TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (artifact_id) REFERENCES artifacts (id),
                UNIQUE(artifact_id, version_number)
            )
        """,
        """
            CREATE TABLE IF NOT EXISTS artifact_collections (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                parent_id TEXT,
                project_id TEXT,
                is_encrypted BOOLEAN DEFAULT 0,
                is_public BOOLEAN DEFAULT 0,
                tags TEXT,
                properties TEXT,
                artifact_count INTEGER DEFAULT 0,
                total_size_bytes INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_id) REFERENCES artifact_collections (id)
            )
        """,
        """
            CREATE TABLE IF NOT EXISTS artifact_permissions (
                id TEXT PRIMARY KEY,
                artifact_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                can_read BOOLEAN DEFAULT 1,
                can_write BOOLEAN DEFAULT 0,
                can_delete BOOLEAN DEFAULT 0,
                can_share BOOLEAN DEFAULT 0,
                granted_by TEXT,
                granted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                expires_at DATETIME,
                FOREIGN KEY (artifact_id) REFERENCES artifacts (id),
                UNIQUE(artifact_id, user_id)
            )
        """,
        "CREATE INDEX IF NOT EXISTS idx_artifacts_name ON artifacts(name)",
        "CREATE INDEX IF NOT EXISTS idx_artifacts_type ON artifacts(content_type)",
        "CREATE INDEX IF NOT EXISTS idx_artifacts_status ON artifacts(status)",
        "CREATE INDEX IF NOT EXISTS idx_artifacts_collection ON artifacts(collection_id)",
        "CREATE INDEX IF NOT EXISTS idx_artifacts_project ON artifacts(project_id)",
        "CREATE INDEX IF NOT EXISTS idx_artifacts_created ON artifacts(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_artifacts_tags ON artifacts(tags)",
        "CREATE INDEX IF NOT EXISTS idx_versions_artifact ON artifact_versions(artifact_id)",
        "CREATE INDEX IF NOT EXISTS idx_versions_number ON artifact_versions(version_number)",
        "CREATE INDEX IF NOT EXISTS idx_collections_name ON artifact_collections(name)",
        "CREATE INDEX IF NOT EXISTS idx_collections_parent ON artifact_collections(parent_id)",
        "CREATE INDEX IF NOT EXISTS idx_permissions_artifact ON artifact_permissions(artifact_id)",
        "CREATE INDEX IF NOT EXISTS idx_permissions_user ON artifact_permissions(user_id)",
    ],
    "file_search": [
        """
            CREATE TABLE IF NOT EXISTS indexed_files (
                id TEXT PRIMARY KEY,
                file_path TEXT UNIQUE NOT NULL,
                file_hash TEXT NOT NULL,
                size INTEGER NOT NULL,
                modified_date DATETIME NOT NULL,
                indexed_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                file_type TEXT,
                status TEXT DEFAULT 'active',
                metadata TEXT
            )
        """,
        """
            CREATE TABLE IF NOT EXISTS file_chunks (
                id TEXT PRIMARY KEY,
                file_id TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                start_pos INTEGER NOT NULL,
                end_pos INTEGER NOT NULL,
                metadata TEXT,
                created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (file_id) REFERENCES indexed_files (id)
                    ON DELETE CASCADE,
                UNIQUE(file_id, chunk_index)
            )
        """,
        """
            CREATE TABLE IF NOT EXISTS file_embeddings (
                id TEXT PRIMARY KEY,
                chunk_id TEXT UNIQUE NOT NULL,
                embedding_vector TEXT NOT NULL,  -- JSON array
                model_name TEXT NOT NULL,
                created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chunk_id) REFERENCES file_chunks (id)
                    ON DELETE CASCADE
            )
        """,
        """
            CREATE TABLE IF NOT EXISTS search_settings (
                id TEXT PRIMARY KEY,
                setting_name TEXT UNIQUE NOT NULL,
                setting_value TEXT NOT NULL,
                created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                modified_date DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """,
        "CREATE INDEX IF NOT EXISTS idx_indexed_files_path ON indexed_files(file_path)",
        "CREATE INDEX IF NOT EXISTS idx_indexed_files_status ON indexed_files(status)",
        "CREATE INDEX IF NOT EXISTS idx_indexed_files_type ON indexed_files(file_type)",
        "CREATE INDEX IF NOT EXISTS idx_file_chunks_file_id ON file_chunks(file_id)",
        "CREATE INDEX IF NOT EXISTS idx_file_chunks_content ON file_chunks(content)",
        "CREATE INDEX IF NOT EXISTS idx_file_embeddings_chunk_id ON file_embeddings(chunk_id)",
        "CREATE INDEX IF NOT EXISTS idx_search_settings_name ON search_settings(setting_name)",
    ],
    "projects": [
        """
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'active' CHECK(status IN ('active', 'completed', 'archived')),
                color TEXT,
                icon TEXT,
                parent_project_id TEXT,
                tags TEXT,
                metadata TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                completed_at DATETIME,
                archived_at DATETIME,
                FOREIGN KEY (parent_project_id) REFERENCES projects (id)
            )
        """,
        "CREATE INDEX IF NOT EXISTS idx_projects_name ON projects(name)",
        "CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status)",
        "CREATE INDEX IF NOT EXISTS idx_projects_parent ON projects(parent_project_id)",
        "CREATE INDEX IF NOT EXISTS idx_projects_created ON projects(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_projects_tags ON projects(tags)",
    ],
    "timers": [
        """
            CREATE TABLE IF NOT EXISTS timer_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_name TEXT,
                start_time DATETIME,
                end_time DATETIME,
                elapsed_seconds REAL
            )
        """,
    ],
}


def _ensure_dir(path: Path) -> None:
    """Ensure a directory exists."""
    path.mkdir(parents=True, exist_ok=True)


def _get_default_user_data_directory() -> Path:
    """Get the default user data directory outside the repository.

    Returns:
        Path: Default user data directory outside the repository
    """
    # Check for environment variable override
    if user_data_path := os.environ.get("DINOAIR_USER_DATA"):
        return Path(user_data_path).expanduser().resolve()

    # For tests, always use temp directory
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return Path(tempfile.gettempdir()) / "DinoAirTests"

    # Platform-specific default locations outside repository
    if os.name == "nt":  # Windows
        # Use AppData/Local for user-specific application data
        app_data = os.environ.get("LOCALAPPDATA", os.path.expanduser("~/AppData/Local"))
        return Path(app_data) / "DinoAir"
    # Unix/Linux/MacOS
    # Follow XDG Base Directory Specification
    xdg_data_home = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
    return Path(xdg_data_home) / "dinoair"


def _validate_user_data_permissions(path: Path) -> None:
    """Validate that the user data directory has proper read/write permissions.

    Args:
        path: Path to validate

    Raises:
        PermissionError: If directory cannot be created or accessed
        OSError: If there are other filesystem issues
    """
    try:
        # Ensure directory exists
        path.mkdir(parents=True, exist_ok=True)

        # Test write permissions by creating a temporary file
        test_file = path / ".dinoair_permission_test"
        try:
            test_file.write_text("test", encoding="utf-8")
            test_file.unlink()  # Clean up test file
        except OSError as e:
            raise PermissionError(f"No write permission for user data directory {path}: {e}") from e

        # Test read permissions
        if not os.access(path, os.R_OK):
            raise PermissionError(f"No read permission for user data directory {path}")

    except OSError as e:
        raise OSError(f"Cannot access user data directory {path}: {e}") from e


def _exec_ddl_batch(conn: sqlite3.Connection, ddls: list[str]) -> None:
    """Execute a batch of DDL statements and commit once at the end."""
    cur = conn.cursor()
    for sql in ddls:
        cur.execute(sql)
    conn.commit()


class DatabaseManager:
    """Manages multiple SQLite databases for the DinoAir application"""

    def __init__(
        self,
        user_name: str | None = None,
        user_feedback: Callable[[str], None] | None = None,
        base_dir: Path | None = None,
    ):
        # Use a separate namespace for tests to avoid polluting real data
        if user_name is None:
            try:
                if os.environ.get("PYTEST_CURRENT_TEST"):
                    self.user_name = "test_user"
                else:
                    self.user_name = "default_user"
            except (OSError, KeyError):
                self.user_name = "default_user"
        else:
            self.user_name = user_name

        self.user_feedback = user_feedback or print

        # Use provided base_dir or get default location outside repository
        if base_dir is not None:
            self.base_dir = Path(base_dir).resolve()
        else:
            self.base_dir = _get_default_user_data_directory()

        # During pytest runs, redirect to an isolated temp directory per process
        try:
            if os.environ.get("PYTEST_CURRENT_TEST"):
                tmp_root = Path(tempfile.gettempdir()) / "DinoAirTests"
                unique = f"run_{os.getpid()}_{int(time.time())}"
                self.base_dir = tmp_root / unique
        except (OSError, KeyError):
            # Fallback silently if temp redirection fails
            pass

        # Validate permissions before proceeding
        try:
            _validate_user_data_permissions(self.base_dir)
        except OSError as e:
            # For tests or when permissions fail, fall back to temp directory
            if os.environ.get("PYTEST_CURRENT_TEST") or "test" in str(self.base_dir).lower():
                temp_fallback = (
                    Path(tempfile.gettempdir()) / "DinoAir_fallback" / f"user_{os.getpid()}"
                )
                self.user_feedback(
                    f"Permission issue with {self.base_dir}, using temp fallback: {temp_fallback}"
                )
                self.base_dir = temp_fallback
                _validate_user_data_permissions(self.base_dir)  # This should work for temp
            else:
                # For production, raise the error
                raise e

        # Resolve user database directory and ensure structure
        self.user_db_dir = self.base_dir / "user_data" / self.user_name / "databases"

        # Track active connections for cleanup
        self._active_connections: list[sqlite3.Connection] = []
        self._connection_lock = threading.Lock()

        # Database file paths (preserve attribute names for compatibility)
        self.notes_db_path = self.user_db_dir / DB_FILES["notes"]
        self.memory_db_path = self.user_db_dir / DB_FILES["memory"]
        self.user_tools_db_path = self.user_db_dir / DB_FILES["user_tools"]
        self.chat_history_db_path = self.user_db_dir / DB_FILES["chat_history"]
        self.appointments_db_path = self.user_db_dir / DB_FILES["appointments"]
        self.artifacts_db_path = self.user_db_dir / DB_FILES["artifacts"]
        self.file_search_db_path = self.user_db_dir / DB_FILES["file_search"]
        self.projects_db_path = self.user_db_dir / DB_FILES["projects"]
        self.timers_db_path = self.user_db_dir / DB_FILES["timers"]

        # Ensure directory structure exists
        self._create_directory_structure()

    def _create_directory_structure(self) -> None:
        """Create the user-specific directory structure"""
        try:
            _ensure_dir(self.user_db_dir)

            # Also create other user-specific folders
            _ensure_dir(self.user_db_dir.parent / "exports")
            _ensure_dir(self.user_db_dir.parent / "backups")
            _ensure_dir(self.user_db_dir.parent / "temp")

            # Create artifact storage directories
            artifacts_dir = self.user_db_dir.parent / "artifacts"
            _ensure_dir(artifacts_dir)

            # Create year/month subdirectories for current date
            now = datetime.now()
            year_dir = artifacts_dir / str(now.year)
            month_dir = year_dir / f"{now.month:02d}"
            _ensure_dir(month_dir)
        except PermissionError:
            self.user_feedback(
                "Cannot create user folders. Please check permissions or run as administrator."
            )
            raise
        except OSError as e:
            self.user_feedback(
                f"OS error creating folders: {str(e)}. Check disk space and permissions."
            )
            raise
        except Exception as e:
            self.user_feedback(f"Unexpected error creating folders: {str(e)}")
            raise

    def _setup_schema(self, db_key: str, conn: sqlite3.Connection) -> None:
        """Apply schema DDLs and run migrations for a given database key."""
        # Apply base schema DDLs first
        if ddls := SCHEMA_DDLS.get(db_key, []):
            _exec_ddl_batch(conn, ddls)

        # Run migrations for the notes database
        if db_key == "notes":
            self._run_notes_migrations(conn)

    def _run_notes_migrations(self, conn: sqlite3.Connection) -> None:
        """Run versioned migrations for the notes database."""
        try:
            # Load all notes migrations
            migrations = get_notes_migrations()

            if not migrations:
                LOGGER.info("No migrations found for notes database")
                return

            # Create migration runner and execute pending migrations
            runner = MigrationRunner(db_key="notes")
            runner.register_migrations(migrations)

            # Run migrations
            executed = runner.run_migrations(conn)

            if executed:
                self.user_feedback(
                    f"[OK] Applied {len(executed)} database migrations: "
                    f"{', '.join(m.full_name for m in executed)}"
                )
            else:
                LOGGER.debug("All migrations already applied for notes database")

        except (ImportError, AttributeError, OSError, sqlite3.Error) as e:
            # Log error but don't fail initialization
            LOGGER.warning("Migration execution failed: %s", e)
            self.user_feedback(f"[WARNING] Migration system error: {str(e)}")
            # Fall back to the old migration method as a safety net
            self._apply_notes_project_id_migration(conn)

    def _apply_notes_project_id_migration(self, conn: sqlite3.Connection) -> None:
        """
        If note_list exists but lacks the project_id column, add it.
        Preserves original behavior.
        """
        cur = conn.cursor()
        try:
            # Check if table exists
            tables = cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            table_names = {t[0] for t in tables}
            if "note_list" in table_names:
                cur.execute("PRAGMA table_info(note_list)")
                columns = [row[1] for row in cur.fetchall()]
                if "project_id" not in columns:
                    cur.execute("ALTER TABLE note_list ADD COLUMN project_id TEXT")
                    self.user_feedback("[OK] Added project_id to existing notes table")
                    conn.commit()
        except sqlite3.Error as e:
            # Log but do not fail initialization if PRAGMA queries fail
            LOGGER.warning("Notes migration check failed: %s", e)

    def _get_connection(self, db_key: str) -> sqlite3.Connection:
        """
        Generic connection factory using ResilientDB with schema setup callback.
        Preserves retry behavior and connection tracking.
        """
        filename = DB_FILES[db_key]
        db_path = self.user_db_dir / filename
        _ensure_dir(db_path.parent)
        db = ResilientDB(db_path, lambda c: self._setup_schema(db_key, c), self.user_feedback)
        conn = db.connect_with_retry()
        self._track_connection(conn)
        return conn

    # Public connection methods (names/signatures preserved)
    def get_notes_connection(self) -> sqlite3.Connection:
        """Get connection to notes database with resilient handling"""
        return self._get_connection("notes")

    def get_memory_connection(self) -> sqlite3.Connection:
        """Get connection to memory database with resilient handling"""
        return self._get_connection("memory")

    def get_user_tools_connection(self) -> sqlite3.Connection:
        """Get connection to user tools database with resilient handling"""
        return self._get_connection("user_tools")

    def get_chat_history_connection(self) -> sqlite3.Connection:
        """Get connection to chat history database with resilient handling"""
        return self._get_connection("chat_history")

    def get_appointments_connection(self) -> sqlite3.Connection:
        """Get connection to appointments database with resilient handling"""
        return self._get_connection("appointments")

    def get_artifacts_connection(self) -> sqlite3.Connection:
        """Get connection to artifacts database with resilient handling"""
        return self._get_connection("artifacts")

    def get_file_search_connection(self) -> sqlite3.Connection:
        """Get connection to file search database with resilient handling"""
        return self._get_connection("file_search")

    def get_projects_connection(self) -> sqlite3.Connection:
        """Get connection to projects database with resilient handling"""
        return self._get_connection("projects")

    def get_timers_connection(self) -> sqlite3.Connection:
        """Get connection to timers database with resilient handling"""
        return self._get_connection("timers")

    # Backward-compat thin wrappers for prior private schema methods (names kept)
    def _setup_notes_schema(self, conn: sqlite3.Connection) -> None:
        self._setup_schema("notes", conn)

    def _setup_memory_schema(self, conn: sqlite3.Connection) -> None:
        self._setup_schema("memory", conn)

    def _setup_user_tools_schema(self, conn: sqlite3.Connection) -> None:
        self._setup_schema("user_tools", conn)

    def _setup_chat_history_schema(self, conn: sqlite3.Connection) -> None:
        self._setup_schema("chat_history", conn)

    def _setup_appointments_schema(self, conn: sqlite3.Connection) -> None:
        self._setup_schema("appointments", conn)

    def _setup_artifacts_schema(self, conn: sqlite3.Connection) -> None:
        self._setup_schema("artifacts", conn)

    def _setup_file_search_schema(self, conn: sqlite3.Connection) -> None:
        self._setup_schema("file_search", conn)

    def _setup_projects_schema(self, conn: sqlite3.Connection) -> None:
        self._setup_schema("projects", conn)

    def _setup_timers_schema(self, conn: sqlite3.Connection) -> None:
        self._setup_schema("timers", conn)

    def initialize_all_databases(self) -> None:
        """Initialize all databases for the user with resilient error handling"""
        self.user_feedback(f"Setting up databases for {self.user_name}...")
        try:
            # Initialize each database with resilient handling in a simple loop
            for db_key in DB_FILES:
                filename = DB_FILES[db_key]
                db_path = self.user_db_dir / filename
                resilient = ResilientDB(
                    db_path,
                    lambda c, k=db_key: self._setup_schema(k, c),
                    self.user_feedback,
                )
                conn = resilient.connect_with_retry()
                conn.close()

            self.user_feedback(f"[OK] All databases ready for {self.user_name}")
        except sqlite3.Error as e:
            self.user_feedback(
                f"[ERROR] Database error: {str(e)}. Please check database file permissions."
            )
            raise
        except PermissionError:
            self.user_feedback(
                "[ERROR] Permission denied. Please run as administrator or check file permissions."
            )
            raise
        except Exception:
            self.user_feedback(
                "[ERROR] Database setup failed. Please try restarting the application or contact support."
            )
            raise

    def _track_connection(self, conn: sqlite3.Connection) -> None:
        """Track a database connection for cleanup"""
        with self._connection_lock:
            self._active_connections.append(conn)

    def _cleanup_connections(self) -> None:
        """Close all tracked database connections"""
        with self._connection_lock:
            for conn in self._active_connections[:]:
                try:
                    if conn:
                        conn.close()
                        self.user_feedback("[OK] Database connection closed")
                except Exception as e:
                    self.user_feedback(f"[WARNING] Error closing connection: {e}")
            self._active_connections.clear()

    def get_watchdog_metrics_manager(self):
        """Get WatchdogMetricsManager instance with memory database connection"""
        from models.watchdog_metrics import WatchdogMetricsManager

        conn = self.get_memory_connection()
        return WatchdogMetricsManager(conn)

    def backup_databases(self) -> None:
        """Create backups of all databases"""
        self.user_feedback("Creating database backups...")
        backup_dir = self.user_db_dir.parent / "backups"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        try:
            _ensure_dir(backup_dir)
            for filename in DB_FILES.values():
                db_path = self.user_db_dir / filename
                if db_path.exists():
                    backup_name = f"{Path(filename).stem}_{timestamp}.db"
                    backup_path = backup_dir / backup_name
                    shutil.copy2(db_path, backup_path)
            self.user_feedback(f"[OK] Backups saved to: {backup_dir}")
        except OSError as e:
            self.user_feedback(f"[ERROR] Backup failed - file system error: {str(e)}")
            raise
        except sqlite3.Error as e:
            self.user_feedback(f"[ERROR] Backup failed - database error: {str(e)}")
            raise
        except Exception as e:
            self.user_feedback(f"[ERROR] Backup failed - unexpected error: {str(e)}")
            raise

    def clean_memory_database(self, watchdog_retention_days: int = 7) -> None:
        """Clean expired entries from memory database and close all connections"""
        try:
            # First cleanup all tracked connections
            self._cleanup_connections()

            # Then clean memory database
            with self.get_memory_connection() as conn:
                cursor = conn.cursor()

                # Remove expired session data
                cursor.execute("DELETE FROM session_data WHERE expires_at < CURRENT_TIMESTAMP")

                # Keep only last 100 recent notes
                cursor.execute(
                    """
                    DELETE FROM recent_notes
                    WHERE note_id NOT IN (
                        SELECT note_id FROM recent_notes
                        ORDER BY accessed_at DESC
                        LIMIT 100
                    )
                """
                )

                # Clean old watchdog metrics based on retention policy (parameterized)
                cutoff = (datetime.now() - timedelta(days=int(watchdog_retention_days))).isoformat()
                cursor.execute(
                    """
                    DELETE FROM watchdog_metrics
                    WHERE timestamp < ?
                    """,
                    (cutoff,),
                )
                deleted_metrics = cursor.rowcount

                conn.commit()

                # Vacuum to reclaim space
                cursor.execute("VACUUM")

                self.user_feedback(
                    f"[OK] Memory database cleaned (removed {deleted_metrics} old metrics)"
                )
        except sqlite3.Error as e:
            self.user_feedback(f"Warning: Database error during cleanup: {str(e)}")
        except Exception as e:
            self.user_feedback(f"Warning: Could not clean memory database: {str(e)}")

    def _cleanup_temp_files(self, stats: dict[str, int]) -> None:
        temp_patterns = ["*.tmp", "*.temp", "*.log", ".temp_*"]
        base_dir = self.user_db_dir.parent
        for pattern in temp_patterns:
            for temp_file in base_dir.glob(f"**/{pattern}"):
                try:
                    if not temp_file.is_file():
                        continue
                    size_mb = temp_file.stat().st_size / (1024 * 1024)
                    temp_file.unlink()
                    stats["files_removed"] += 1
                    stats["space_freed_mb"] += size_mb
                    if hasattr(self, "user_feedback"):
                        self.user_feedback(f"Removed temp file: {temp_file.name}")
                except OSError:
                    continue

    def _cleanup_old_backups(self, stats: dict[str, int], max_backup_age_days: int) -> None:
        cutoff_time = time.time() - (max_backup_age_days * 24 * 3600)
        backup_patterns = ["*backup*", "*.bak", "*_old*"]
        base_dir = self.user_db_dir.parent
        for pattern in backup_patterns:
            for backup_file in base_dir.glob(f"**/{pattern}"):
                try:
                    if not backup_file.is_file() or backup_file.stat().st_mtime >= cutoff_time:
                        continue
                    size_mb = backup_file.stat().st_size / (1024 * 1024)
                    backup_file.unlink()
                    stats["backups_removed"] += 1
                    if hasattr(self, "user_feedback"):
                        self.user_feedback(f"Removed backup file: {backup_file.name}")
                except OSError:
                    continue

    def cleanup_user_data(
        self,
        cleanup_temp_files: bool = True,
        cleanup_old_backups: bool = True,
        max_backup_age_days: int = 30,
    ) -> dict[str, int]:
        """Comprehensive cleanup of user data for development and testing.

        Args:
            cleanup_temp_files: Whether to clean temporary files
            cleanup_old_backups: Whether to clean old backup files
            max_backup_age_days: Maximum age for backup files to keep

        Returns:
            Dict with cleanup statistics
        """
        stats = {"files_removed": 0, "space_freed_mb": 0, "backups_removed": 0}

        try:
            # 1. Clean memory database first
            self.clean_memory_database()

            # 2. Clean temporary files in user directory
            if cleanup_temp_files:
                self._cleanup_temp_files(stats)

            # 3. Clean old backup files
            if cleanup_old_backups:
                self._cleanup_old_backups(stats, max_backup_age_days)

            # 4. Vacuum all databases to reclaim space
            db_connections = [
                ("notes", self.get_notes_connection),
                ("appointments", self.get_appointments_connection),
                ("artifacts", self.get_artifacts_connection),
                ("projects", self.get_projects_connection),
                ("file_search", self.get_file_search_connection),
                ("chat_history", self.get_chat_history_connection),
                ("user_tools", self.get_user_tools_connection),
                ("timers", self.get_timers_connection),
            ]

            for db_name, get_connection in db_connections:
                try:
                    with get_connection() as conn:
                        conn.execute("VACUUM")
                        if hasattr(self, "user_feedback"):
                            self.user_feedback(f"Vacuumed {db_name} database")
                except (sqlite3.Error, OSError):
                    pass  # Continue with other databases

            stats["space_freed_mb"] = round(stats["space_freed_mb"], 2)

            if hasattr(self, "user_feedback"):
                self.user_feedback(
                    f"[OK] User data cleanup completed: "
                    f"{stats['files_removed']} files removed, "
                    f"{stats['backups_removed']} old backups removed, "
                    f"{stats['space_freed_mb']} MB freed"
                )
        except Exception as e:
            if hasattr(self, "user_feedback"):
                self.user_feedback(f"Warning: Error during user data cleanup: {str(e)}")

        return stats


# For easy initialization when GUI starts
def initialize_user_databases(
    user_name: str | None = None,
    user_feedback: Callable[[str], None] | None = None,
    base_dir: Path | None = None,
) -> DatabaseManager:
    """Convenience function to initialize databases for a user

    Args:
        user_name: User name for database isolation (defaults based on test context)
        user_feedback: Function to provide setup feedback (defaults to print)
        base_dir: Base directory for user data (defaults to platform-appropriate location outside repo)

    Returns:
        DatabaseManager: Initialized database manager
    """
    # Default user_feedback to print if not provided
    if user_feedback is None:
        user_feedback = print

    # Always use consistent 3-parameter constructor
    manager = DatabaseManager(user_name, user_feedback, base_dir)
    manager.initialize_all_databases()
    return manager


# Example usage in your GUI application:
if __name__ == "__main__":
    # Test with console feedback
    def console_feedback(message: str) -> None:
        pass

    # Initialize for default user
    try:
        db_manager = initialize_user_databases("john_doe", console_feedback)
        console_feedback("Database setup completed successfully!")
    except sqlite3.Error as e:
        console_feedback(f"Database setup failed: {e}")
    except PermissionError as e:
        console_feedback(f"Permission error during setup: {e}")
    except Exception as e:
        console_feedback(f"Setup failed: {e}")

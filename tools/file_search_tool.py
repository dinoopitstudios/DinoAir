"""
File Search Tool Functions for DinoAir 2.0 AI Integration

This module provides AI-accessible functions for the RAG-powered file search
system, enabling AI models to programmatically interact with file indexing,
search, and retrieval operations.

All functions follow the standard tool pattern with comprehensive
documentation and error handling for proper AI discovery and usage.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from tools.common.db import get_file_search_db
from tools.common.logging_utils import log_exception
from tools.common.validators import (
    validate_list_non_empty,
    validate_non_empty_str,
    validate_path_exists,
)

logger = logging.getLogger(__name__)


def _map_validate_path_error(e: ValueError, file_path: str) -> dict:
    msg = str(e)
    if msg == "file_path is required":
        return {
            "success": False,
            "error": "file_path is required",
            "message": "Failed to index file: file_path is required",
        }

    try:
        # Prefer centralized classifier; falls back to direct message checks if unavailable
        # type: ignore[import-untyped]
        from tools.common.validators import _classify_path_error

        # "not_found" | "not_file" | "not_dir" | "other"
        kind = _classify_path_error(e)
    except Exception:
        kind = "other"

    if kind == "not_found" or msg.startswith("Path does not exist:"):
        return {
            "success": False,
            "error": f"File does not exist: {file_path}",
            "message": f"Cannot index non-existent file: {file_path}",
        }
    if kind == "not_file" or msg.startswith("Path is not a file:"):
        return {
            "success": False,
            "error": f"Path is not a file: {file_path}",
            "message": f"Cannot index directory: {file_path}",
        }
    if kind == "not_dir" or msg.startswith("Path is not a directory:"):
        # Keep outward message patterns consistent even if not_dir is encountered
        return {
            "success": False,
            "error": f"Path is not a directory: {file_path}",
            "message": f"Failed to index file: Path is not a directory: {file_path}",
        }
    return {
        "success": False,
        "error": msg,
        "message": f"Failed to index file: {msg}",
    }


def _build_file_info_response(
    path_obj: Path,
    file_hash: str,
    file_size: int,
    resolved_type: str,
    modified_date: datetime,
) -> dict:
    return {
        "path": str(path_obj),
        "size": file_size,
        "type": resolved_type,
        "hash": file_hash,
        "modified_date": modified_date.isoformat(),
    }


def _handle_db_add_result(db_result: dict, file_info: dict) -> dict:
    if db_result.get("success"):
        return {
            "success": True,
            "file_id": db_result.get("file_id", ""),
            "message": db_result.get("message", ""),
            "file_info": file_info,
        }
    err = db_result.get("error", "")
    return {
        "success": False,
        "error": err,
        "message": f"Failed to index file: {err}",
    }


def _compute_file_metadata(path_obj: Path, file_type: str | None) -> tuple[str, int, datetime, str]:
    """
    Compute file hash, size, modified date, and resolved type.

    Args:
        path_obj (Path): Path object for the file.
        file_type (Optional[str]): Provided file type or None.

    Returns:
        Tuple[str, int, datetime, str]: (file_hash, file_size, modified_date, resolved_type)
    """
    import hashlib

    with open(path_obj, "rb") as f:
        file_hash = hashlib.sha256(f.read()).hexdigest()

    file_size = path_obj.stat().st_size
    modified_date = datetime.fromtimestamp(path_obj.stat().st_mtime)
    resolved_type = file_type if file_type else path_obj.suffix.lower().lstrip(".")

    return file_hash, file_size, modified_date, resolved_type


def search_files_by_keywords(
    keywords: list[str],
    limit: int = 10,
    file_types: list[str] | None = None,
    file_paths: list[str] | None = None,
    user_name: str = "default_user",
) -> dict[str, Any]:
    """
    Search indexed files using keyword-based search.

    Performs keyword search across indexed file contents with optional
    filtering by file types and paths for AI-driven document retrieval.

    Args:
        keywords (List[str]): List of keywords to search for
        limit (int): Maximum number of results to return (default: 10)
        file_types (Optional[List[str]]): Filter by file types
                                         (e.g., ['pdf', 'txt'])
        file_paths (Optional[List[str]]): Filter by specific file paths
        user_name (str): Username for database operations

    Returns:
        Dict[str, Any]: A dictionary containing:
            - success (bool): Whether the operation was successful
            - results (List[Dict]): List of matching file chunks with relevance
            - count (int): Number of results found
            - keywords (List[str]): Keywords that were searched
            - message (str): Success or error message

    Example:
        >>> search_files_by_keywords(["python", "function"], limit=5)
        {
            'success': True,
            'results': [{'chunk_id': 'abc_1', 'content': '...',
                        'relevance_score': 0.8}],
            'count': 3,
            'keywords': ['python', 'function'],
            'message': 'Found 3 matching chunks'
        }
    """
    try:
        try:
            validate_list_non_empty("keywords", keywords)
        except ValueError:
            return {
                "success": False,
                "error": "keywords list is required and cannot be empty",
                "message": "Failed to search: no keywords provided",
            }

        # Initialize database
        file_search_db = get_file_search_db(user_name)

        # Perform keyword search
        results = file_search_db.search_by_keywords(
            keywords=keywords, limit=limit, file_types=file_types, file_paths=file_paths
        )

        return {
            "success": True,
            "results": results,
            "count": len(results),
            "keywords": keywords,
            "limit": limit,
            "file_types": file_types,
            "file_paths": file_paths,
            "message": f"Found {len(results)} matching chunks",
        }

    except Exception as e:
        log_exception(logger, f"Error searching files by keywords {keywords}", e)
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to search files: {str(e)}",
        }


def get_file_info(file_path: str, user_name: str = "default_user") -> dict[str, Any]:
    """
    Retrieve information about an indexed file.

    Gets comprehensive metadata about a file in the search index
    for AI-driven file analysis and management workflows.

    Args:
        file_path (str): Path to the file to get information about
        user_name (str): Username for database operations

    Returns:
        Dict[str, Any]: A dictionary containing:
            - success (bool): Whether the operation was successful
            - file_info (Dict): File metadata and indexing information
            - message (str): Success or error message

    Example:
        >>> get_file_info("/path/to/document.pdf")
        {
            'success': True,
            'file_info': {'id': 'file_123', 'size': 1024, 'type': 'pdf', ...},
            'message': 'File information retrieved successfully'
        }
    """
    try:
        try:
            validate_non_empty_str("file_path", file_path)
        except ValueError:
            return {
                "success": False,
                "error": "file_path is required",
                "message": "Failed to get file info: file_path is required",
            }

        # Initialize database
        file_search_db = get_file_search_db(user_name)

        # Get file information
        file_info = file_search_db.get_file_by_path(file_path)

        if file_info:
            return {
                "success": True,
                "file_info": file_info,
                "message": "File information retrieved successfully",
            }
        return {
            "success": False,
            "error": f"File not found in index: {file_path}",
            "message": f"File '{file_path}' is not in the search index",
        }

    except Exception as e:
        log_exception(logger, f"Error getting file info for {file_path}", e)
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to get file info: {str(e)}",
        }


def add_file_to_index(
    file_path: str,
    file_type: str | None = None,
    metadata: dict[str, Any] | None = None,
    user_name: str = "default_user",
) -> dict[str, Any]:
    """
    Add a file to the search index.

    Indexes a file for search by calculating its hash, extracting metadata,
    and adding it to the searchable database for AI-driven document indexing.

    Args:
        file_path (str): Path to the file to index
        file_type (Optional[str]): Type of the file (e.g., 'pdf', 'txt')
        metadata (Optional[Dict]): Additional metadata for the file
        user_name (str): Username for database operations

    Returns:
        Dict[str, Any]: A dictionary containing:
            - success (bool): Whether the operation was successful
            - file_id (str): ID of the indexed file (if successful)
            - message (str): Success or error message

    Example:
        >>> add_file_to_index("/path/to/document.pdf", "pdf")
        {
            'success': True,
            'file_id': 'file_abc123',
            'message': 'File indexed successfully'
        }
    """
    try:
        # Validate input presence exactly as before
        try:
            validate_non_empty_str("file_path", file_path)
        except ValueError:
            return {
                "success": False,
                "error": "file_path is required",
                "message": "Failed to index file: file_path is required",
            }

        # Validate and resolve path; map errors via helper to preserve messages
        try:
            path_obj = validate_path_exists(file_path, must_be_file=True)
        except ValueError as ve:
            return _map_validate_path_error(ve, file_path)

        # Compute metadata via helper
        file_hash, file_size, modified_date, resolved_type = _compute_file_metadata(
            path_obj, file_type
        )

        # Initialize database and add file
        file_search_db = get_file_search_db(user_name)
        result = file_search_db.add_indexed_file(
            file_path=str(path_obj),
            file_hash=file_hash,
            size=file_size,
            modified_date=modified_date,
            file_type=resolved_type,
            metadata=metadata,
        )

        # Build file_info and handle DB result via helper
        file_info = _build_file_info_response(
            path_obj, file_hash, file_size, resolved_type, modified_date
        )
        return _handle_db_add_result(result, file_info)

    except Exception as e:
        log_exception(logger, f"Error adding file to index {file_path}", e)
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to index file: {str(e)}",
        }


def remove_file_from_index(file_path: str, user_name: str = "default_user") -> dict[str, Any]:
    """
    Remove a file from the search index.

    Removes a file and all its associated data (chunks, embeddings)
    from the search index for AI-driven index management.

    Args:
        file_path (str): Path to the file to remove from index
        user_name (str): Username for database operations

    Returns:
        Dict[str, Any]: A dictionary containing:
            - success (bool): Whether the operation was successful
            - message (str): Success or error message

    Example:
        >>> remove_file_from_index("/path/to/old_document.pdf")
        {
            'success': True,
            'message': 'File removed from index successfully'
        }
    """
    try:
        try:
            validate_non_empty_str("file_path", file_path)
        except ValueError:
            return {
                "success": False,
                "error": "file_path is required",
                "message": "Failed to remove file: file_path is required",
            }

        # Initialize database
        file_search_db = get_file_search_db(user_name)

        # Remove file from index
        result = file_search_db.remove_file_from_index(file_path)

        if result["success"]:
            return {"success": True, "message": result["message"]}
        return {
            "success": False,
            "error": result["error"],
            "message": f"Failed to remove file: {result['error']}",
        }

    except Exception as e:
        log_exception(logger, f"Error removing file from index {file_path}", e)
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to remove file: {str(e)}",
        }


def get_search_statistics(user_name: str = "default_user") -> dict[str, Any]:
    """
    Get comprehensive statistics about the file search index.

    Provides detailed information about indexed files, chunks, embeddings,
    and storage usage for AI-driven index monitoring and analysis.

    Args:
        user_name (str): Username for database operations

    Returns:
        Dict[str, Any]: A dictionary containing:
            - success (bool): Whether the operation was successful
            - stats (Dict): Comprehensive indexing statistics
            - message (str): Success or error message

    Example:
        >>> get_search_statistics()
        {
            'success': True,
            'stats': {'total_files': 150, 'total_chunks': 5000, ...},
            'message': 'Statistics retrieved successfully'
        }
    """
    try:
        # Initialize database
        file_search_db = get_file_search_db(user_name)

        # Get statistics
        stats = file_search_db.get_indexed_files_stats()

        return {
            "success": True,
            "stats": stats,
            "message": "Statistics retrieved successfully",
        }

    except Exception as e:
        log_exception(logger, "Error getting search statistics", e)
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to get statistics: {str(e)}",
        }


def manage_search_directories(
    action: str, directory: str, user_name: str = "default_user"
) -> dict[str, Any]:
    """
    Manage allowed and excluded directories for file search.

    Controls which directories are included or excluded from
    file indexing operations for AI-driven directory management.

    Args:
        action (str): Action to perform - "add_allowed", "remove_allowed",
                     "add_excluded", "remove_excluded", or "get_settings"
        directory (str): Directory path to manage
                        (not needed for "get_settings")
        user_name (str): Username for database operations

    Returns:
        Dict[str, Any]: A dictionary containing:
            - success (bool): Whether the operation was successful
            - message (str): Success or error message
            - settings (Dict): Directory settings (for "get_settings" action)

    Example:
        >>> manage_search_directories("add_allowed", "/home/user/documents")
        {
            'success': True,
            'message': 'Directory added to allowed list'
        }
    """
    try:
        valid_actions = [
            "add_allowed",
            "remove_allowed",
            "add_excluded",
            "remove_excluded",
            "get_settings",
        ]

        if action not in valid_actions:
            return {
                "success": False,
                "error": f"Invalid action. Must be one of: {valid_actions}",
                "message": f"Invalid action '{action}' specified",
            }

        # Initialize database
        file_search_db = get_file_search_db(user_name)

        if action == "get_settings":
            # Get directory settings
            result = file_search_db.get_directory_settings()
            if result["success"]:
                return {
                    "success": True,
                    "settings": {
                        "allowed_directories": result["allowed_directories"],
                        "excluded_directories": result["excluded_directories"],
                        "total_allowed": result["total_allowed"],
                        "total_excluded": result["total_excluded"],
                    },
                    "message": "Directory settings retrieved successfully",
                }
            return {
                "success": False,
                "error": result["error"],
                "message": f"Failed to get settings: {result['error']}",
            }

        # For other actions, directory is required
        if not directory:
            return {
                "success": False,
                "error": "directory is required for this action",
                "message": f"Directory path required for action '{action}'",
            }

        # Perform the requested action
        result = None
        if action == "add_allowed":
            result = file_search_db.add_allowed_directory(directory)
        elif action == "remove_allowed":
            result = file_search_db.remove_allowed_directory(directory)
        elif action == "add_excluded":
            result = file_search_db.add_excluded_directory(directory)
        elif action == "remove_excluded":
            result = file_search_db.remove_excluded_directory(directory)

        if result and result["success"]:
            return {
                "success": True,
                "message": result["message"],
                "action": action,
                "directory": directory,
            }
        if result:
            return {
                "success": False,
                "error": result["error"],
                "message": f"Failed to {action}: {result['error']}",
            }
        return {
            "success": False,
            "error": f"Unknown action or operation failed: {action}",
            "message": f"Failed to perform action: {action}",
        }

    except Exception as e:
        log_exception(logger, f"Error managing directories with action {action}", e)
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to manage directories: {str(e)}",
        }


def optimize_search_database(user_name: str = "default_user") -> dict[str, Any]:
    """
    Optimize the file search database for better performance.

    Performs database optimization including vacuuming, analyzing,
    and updating statistics for AI-driven database maintenance.

    Args:
        user_name (str): Username for database operations

    Returns:
        Dict[str, Any]: A dictionary containing:
            - success (bool): Whether the operation was successful
            - stats (Dict): Post-optimization table statistics
            - message (str): Success or error message

    Example:
        >>> optimize_search_database()
        {
            'success': True,
            'stats': {'indexed_files': 150, 'file_chunks': 5000},
            'message': 'Database optimized successfully'
        }
    """
    try:
        # Initialize database
        file_search_db = get_file_search_db(user_name)

        # Perform optimization
        result = file_search_db.optimize_database()

        if result["success"]:
            return {
                "success": True,
                "stats": result.get("table_stats", {}),
                "message": result["message"],
            }
        return {
            "success": False,
            "error": result["error"],
            "message": f"Failed to optimize database: {result['error']}",
        }

    except Exception as e:
        log_exception(logger, "Error optimizing search database", e)
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to optimize database: {str(e)}",
        }


def get_file_embeddings(file_path: str, user_name: str = "default_user") -> dict[str, Any]:
    """
    Retrieve embeddings for a specific indexed file.

    Gets all vector embeddings and chunks associated with a file
    for AI-driven semantic analysis and similarity operations.

    Args:
        file_path (str): Path to the file to get embeddings for
        user_name (str): Username for database operations

    Returns:
        Dict[str, Any]: A dictionary containing:
            - success (bool): Whether the operation was successful
            - embeddings (List[Dict]): List of embeddings with chunk info
            - count (int): Number of embeddings found
            - file_path (str): Path of the file
            - message (str): Success or error message

    Example:
        >>> get_file_embeddings("/path/to/document.pdf")
        {
            'success': True,
            'embeddings': [{'chunk_id': 'abc_1', 'content': '...'}],
            'count': 10,
            'message': 'Found 10 embeddings for file'
        }
    """
    try:
        try:
            validate_non_empty_str("file_path", file_path)
        except ValueError:
            return {
                "success": False,
                "error": "file_path is required",
                "message": "Failed to get embeddings: file_path is required",
            }

        # Initialize database
        file_search_db = get_file_search_db(user_name)

        # Get embeddings for file
        embeddings = file_search_db.get_embeddings_by_file(file_path)

        return {
            "success": True,
            "embeddings": embeddings,
            "count": len(embeddings),
            "file_path": file_path,
            "message": f"Found {len(embeddings)} embeddings for file",
        }

    except Exception as e:
        log_exception(logger, f"Error getting embeddings for file {file_path}", e)
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to get embeddings: {str(e)}",
        }


# Tool registry for discovery
FILE_SEARCH_TOOLS = {
    "search_files_by_keywords": search_files_by_keywords,
    "get_file_info": get_file_info,
    "add_file_to_index": add_file_to_index,
    "remove_file_from_index": remove_file_from_index,
    "get_search_statistics": get_search_statistics,
    "manage_search_directories": manage_search_directories,
    "optimize_search_database": optimize_search_database,
    "get_file_embeddings": get_file_embeddings,
}

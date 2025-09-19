#!/usr/bin/env python3
"""
Quick cleanup script for DinoAir development

This provides a simple interface to run cleanup operations during development.
"""

import sys
from pathlib import Path

from utils.dev_cleanup import UserDataCleanupManager

# Add the parent directory to the path so we can import DinoAir modules
sys.path.insert(0, str(Path(__file__).parent.parent))


def quick_cleanup():
    """Perform a quick cleanup for development."""
    print("DinoAir Development Cleanup")
    print("=" * 40)

    cleanup_manager = UserDataCleanupManager(dry_run=False, verbose=True)

    # First analyze what we have
    print("\n1. Analyzing current state...")
    analysis = cleanup_manager.analyze_user_data()

    total_size = sum(
        info.get("size_mb", 0) for info in analysis.values() if info.get("status") == "found"
    )

    if total_size > 0:
        print(f"\nFound {total_size:.2f} MB of user data across {len(analysis)} locations")

        # Ask user if they want to proceed
        response = input("\nProceed with cleanup? (y/N): ").strip().lower()
        if response in ["y", "yes"]:
            print("\n2. Performing cleanup...")
            results = cleanup_manager.full_cleanup(
                max_age_hours=1,  # Very aggressive for development
                cleanup_repo=True,
                backup_repo_data=False,  # No backup needed for dev cleanup
            )

            summary = results.get("summary", {})
            print("\nCleanup completed!")
            print(f"Space freed: {summary.get('total_space_freed_mb', 0):.2f} MB")
            print(f"Items removed: {summary.get('total_items_removed', 0)}")
        else:
            print("Cleanup cancelled.")
    else:
        print("No user data found to clean up.")


if __name__ == "__main__":
    try:
        quick_cleanup()
    except KeyboardInterrupt:
        print("\nCleanup cancelled by user.")
    except (OSError, ImportError) as e:
        print(f"Error during cleanup: {e}")
        sys.exit(1)

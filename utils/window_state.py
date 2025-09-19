"""
Window state persistence manager for saving and restoring window geometry,
state, and splitter positions across application sessions.
"""

import json
import os
from typing import TYPE_CHECKING, Any, cast

import aiofiles

from .logger import Logger
from .scaling import ScalingHelper, get_scaling_helper  # noqa: F401 - needed for test compatibility

if TYPE_CHECKING:
    from PySide6.QtCore import QRect, Qt  # type: ignore
    from PySide6.QtWidgets import QSplitter, QWidget  # type: ignore
else:
    try:
        from PySide6.QtCore import QRect, Qt  # type: ignore
        from PySide6.QtWidgets import QSplitter, QWidget  # type: ignore
    except ImportError:  # pragma: no cover - fallbacks when PySide6 not available

        class QRect:  # type: ignore
            """Fallback QRect class for geometry representation when PySide6 is unavailable."""

            def __init__(self, *_: Any, **__: Any) -> None:
                pass

        class _QtFallback:  # type: ignore
            """Fallback Qt namespace providing Qt constants when PySide6 is unavailable."""

            class Orientation:
                """Wrapper for Qt Orientation constants."""

                Horizontal = 1
                Vertical = 2

        Qt = _QtFallback()  # type: ignore

        class QWidget:  # type: ignore
            """Fallback QWidget class providing basic widget functionality when PySide6 is unavailable."""

            @staticmethod
            def isMaximized() -> bool:
                return False

            @staticmethod
            def geometry() -> Any:
                class _G:
                    """Helper class representing geometry properties of a widget."""

                    def x(self) -> int:
                        return 0

                    def y(self) -> int:
                        return 0

                    def width(self) -> int:
                        return 0

                    def height(self) -> int:
                        return 0

                return _G()

            @staticmethod
            def setGeometry(*_: Any, **__: Any) -> None:
                pass

            @staticmethod
            def showMaximized() -> None:
                pass

        class QSplitter:  # type: ignore
            """Fallback QSplitter class providing basic splitter functionality when PySide6 is unavailable."""

            @staticmethod
            def sizes() -> list[int]:
                return [50, 50]

            @staticmethod
            def setSizes(*_: Any, **__: Any) -> None:
                pass

            def orientation(self) -> int:
                return 1

            def width(self) -> int:
                return 100

            def height(self) -> int:
                return 100


try:
    from .error_handling import error_aggregator, safe_operation
except ImportError:

    def safe_operation(func, *args, **kwargs):
        return func(*args, **kwargs)

    error_aggregator = None


class WindowStateManager:
    """Manages window state persistence for application sessions."""

    def __init__(self):
        """Initialize the WindowStateManager."""
        self.logger = Logger()
        self.config_dir = "config"
        self.state_file = os.path.join(self.config_dir, "window_state.json")
        self._ensure_config_dir()
        self.state_data = self._load_state()

    def _ensure_config_dir(self):
        """Ensure the config directory exists."""
        if not os.path.exists(self.config_dir):
            try:
                os.makedirs(self.config_dir)
            except OSError as e:
                self.logger.error(f"Failed to create config directory: {e}")
                if error_aggregator:
                    error_aggregator.record_error(e, "_ensure_config_dir")

    def _load_from_file(self, *args, **kwargs):
        """Load JSON data from state file using context manager.

        Args:
            *args: Unused arguments (for compatibility with safe_operation)
            **kwargs: Unused keyword arguments (for compatibility with safe_operation)

        Returns:
            Loaded JSON data from the state file

        Raises:
            Various exceptions that can occur during file operations
        """
        with open(self.state_file, encoding="utf-8") as f:
            return json.load(f)

    def _load_state(self) -> dict[str, Any]:
        """Load state from JSON file or return default state."""
        default_state: dict[str, Any] = {
            "window": {
                "geometry": [100, 100, 1200, 800],  # x, y, width, height
                "maximized": False,
                "zoom_level": 1.0,
            },
            "splitters": {
                "main_bottom": [70, 30],  # percentages
                "notes_content": [30, 70],
                "notes_tag_panel": 250,  # scaled width
            },
        }

        if not os.path.exists(self.state_file):
            return default_state

        loaded_state = safe_operation(self._load_from_file, default_state)
        if loaded_state == default_state or loaded_state is None:
            return default_state

        loaded_state = cast("dict[str, Any]", loaded_state)
        # Merge with default to ensure all keys exist with proper typing
        for key, def_val in default_state.items():
            if key not in loaded_state:
                loaded_state[key] = def_val
            elif isinstance(def_val, dict) and isinstance(loaded_state.get(key), dict):
                def_val_dict: dict[str, Any] = cast("dict[str, Any]", def_val)
                dst: dict[str, Any] = cast("dict[str, Any]", loaded_state[key])
                for subkey, subdef in def_val_dict.items():
                    if subkey not in dst:
                        dst[subkey] = subdef
                loaded_state[key] = dst
        return loaded_state

    async def _load_state_async(self) -> dict[str, Any]:
        """Load state from JSON file asynchronously or return default state."""
        default_state: dict[str, Any] = {
            "window": {
                "geometry": [100, 100, 1200, 800],  # x, y, width, height
                "maximized": False,
                "zoom_level": 1.0,
            },
            "splitters": {
                "main_bottom": [70, 30],  # percentages
                "notes_content": [30, 70],
                "notes_tag_panel": 250,  # scaled width
            },
        }

        if not os.path.exists(self.state_file):
            return default_state

        try:
            async with aiofiles.open(self.state_file, encoding="utf-8") as f:
                content = await f.read()
                loaded_state = json.loads(content)
        except (OSError, json.JSONDecodeError):
            return default_state

        loaded_state = cast("dict[str, Any]", loaded_state)
        # Merge with default to ensure all keys exist with proper typing
        for key, def_val in default_state.items():
            if key not in loaded_state:
                loaded_state[key] = def_val
            elif isinstance(def_val, dict) and isinstance(loaded_state.get(key), dict):
                def_val_dict: dict[str, Any] = cast("dict[str, Any]", def_val)
                dst: dict[str, Any] = cast("dict[str, Any]", loaded_state[key])
                for subkey, subdef in def_val_dict.items():
                    if subkey not in dst:
                        dst[subkey] = subdef
                loaded_state[key] = dst
        return loaded_state

    def _save_state(self):
        """Save current state to JSON file."""
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(self.state_data, f, indent=2)
            self.logger.info("Window state saved successfully")
        except Exception as e:
            self.logger.error(f"Failed to save window state: {e}")
            if error_aggregator:
                error_aggregator.record_error(e, "_save_state")

    async def _save_state_async(self):
        """Save current state to JSON file asynchronously."""
        try:
            async with aiofiles.open(self.state_file, "w", encoding="utf-8") as f:
                content = json.dumps(self.state_data, indent=2)
                await f.write(content)
        except OSError as e:
            self.logger.error(f"Failed to save window state asynchronously: {e}")
            if error_aggregator:
                error_aggregator.record_error(e, "_save_state_async")

    def save_window_state(self, window: QWidget):
        """
        Save window geometry and state.

        Args:
            window: The main window widget
        """
        try:
            # Save geometry
            geometry = window.geometry()
            self.state_data["window"]["geometry"] = [
                geometry.x(),
                geometry.y(),
                geometry.width(),
                geometry.height(),
            ]

            # Save maximized state
            self.state_data["window"]["maximized"] = window.isMaximized()

            self._save_state()
        except Exception as e:
            self.logger.error(f"Failed to save window state: {e}")

    async def save_window_state_async(self, window: QWidget):
        """
        Save window geometry and state asynchronously.

        Args:
            window: The main window widget
        """
        try:
            # Only save geometry if window is not maximized
            if not window.isMaximized():
                geometry = window.geometry()
                self.state_data["window"]["geometry"] = [
                    geometry.x(),
                    geometry.y(),
                    geometry.width(),
                    geometry.height(),
                ]

            # Save maximized state
            self.state_data["window"]["maximized"] = window.isMaximized()

            await self._save_state_async()
            self.logger.info("Window state saved successfully (async)")
        except OSError as e:
            self.logger.error(f"Failed to save window state asynchronously: {e}")
            if error_aggregator:
                error_aggregator.record_error(e, "save_window_state_async")

    def restore_window_state(self, window: QWidget):
        """
        Restore window geometry and state.

        Args:
            window: The main window widget
        """
        try:
            # Restore geometry
            geometry = self.state_data["window"]["geometry"]
            window.setGeometry(geometry[0], geometry[1], geometry[2], geometry[3])

            # Restore maximized state
            if self.state_data.get("window", {}).get("maximized", False):
                window.showMaximized()

            self.logger.info("Window state restored successfully")
        except RuntimeError as e:
            self.logger.error(f"Failed to restore window state: {e}")
            if error_aggregator:
                error_aggregator.record_error(e, "restore_window_state")

    async def restore_window_state_async(self, window: QWidget):
        """
        Restore window geometry and state asynchronously.

        Args:
            window: The main window widget
        """
        try:
            # Load state asynchronously first
            self.state_data = await self._load_state_async()

            # Restore geometry
            geometry = self.state_data["window"]["geometry"]
            window.setGeometry(QRect(geometry[0], geometry[1], geometry[2], geometry[3]))

            # Restore maximized state
            if self.state_data["window"]["maximized"]:
                window.showMaximized()

            self.logger.info("Window state restored successfully (async)")
        except RuntimeError as e:
            self.logger.error(f"Failed to restore window state asynchronously: {e}")
            if error_aggregator:
                error_aggregator.record_error(e, "restore_window_state_async")

    def save_zoom_level(self, zoom_level: float):
        """
        Save user zoom preference.

        Args:
            zoom_level: The zoom level to save
        """
        try:
            self.state_data["window"]["zoom_level"] = zoom_level
            self._save_state()
            self.logger.info(f"Zoom level saved: {zoom_level}")
        except RuntimeError as e:
            self.logger.error(f"Failed to save zoom level: {e}")
            if error_aggregator:
                error_aggregator.record_error(e, "save_zoom_level")

    async def save_zoom_level_async(self, zoom_level: float):
        """
        Save user zoom preference asynchronously.

        Args:
            zoom_level: The zoom level to save
        """
        try:
            self.state_data["window"]["zoom_level"] = zoom_level
            await self._save_state_async()
            self.logger.info(f"Zoom level saved asynchronously: {zoom_level}")
        except RuntimeError as e:
            self.logger.error(f"Failed to save zoom level asynchronously: {e}")
            if error_aggregator:
                error_aggregator.record_error(e, "save_zoom_level_async")

    def get_zoom_level(self) -> float:
        """
        Retrieve saved zoom level.

        Returns:
            The saved zoom level, or 1.0 if not found
        """
        return self.state_data.get("window", {}).get("zoom_level", 1.0)

    def save_splitter_state(self, splitter_name: str, sizes: list[int]):
        """
        Save splitter sizes directly as provided.

        Args:
            splitter_name: Identifier for the splitter
            sizes: List of sizes from the splitter
        """
        try:
            self.state_data["splitters"][splitter_name] = sizes
            self._save_state()
            self.logger.info(f"Splitter state saved: {splitter_name}")
        except RuntimeError as e:
            self.logger.error(f"Failed to save splitter state: {e}")
            if error_aggregator:
                error_aggregator.record_error(e, "save_splitter_state")

    async def save_splitter_state_async(self, splitter_name: str, sizes: list[int]):
        """
        Save splitter sizes as percentages or scaled values asynchronously.

        Args:
            splitter_name: Identifier for the splitter
            sizes: List of sizes from the splitter
        """
        try:
            if splitter_name == "notes_tag_panel":
                # For tag panel, save the scaled width directly
                if sizes:
                    self.state_data["splitters"][splitter_name] = sizes[0]
                else:
                    self.state_data["splitters"][splitter_name] = 250
            else:
                # For other splitters, save as percentages
                total = sum(sizes)
                if total > 0:
                    percentages = [int(size * 100 / total) for size in sizes]
                    self.state_data["splitters"][splitter_name] = percentages

            await self._save_state_async()
            self.logger.info(f"Splitter state saved asynchronously: {splitter_name}")
        except RuntimeError as e:
            self.logger.error(f"Failed to save splitter state asynchronously: {e}")
            if error_aggregator:
                error_aggregator.record_error(e, "save_splitter_state_async")

    def get_splitter_state(self, splitter_name: str) -> list[int] | None:
        """
        Get saved splitter state.

        Args:
            splitter_name: Identifier for the splitter

        Returns:
            List of sizes/percentages, or None if not found
        """
        return self.state_data.get("splitters", {}).get(splitter_name)

    def save_splitter_from_widget(self, splitter_name: str, splitter: QSplitter):
        """
        Save splitter state directly from a QSplitter widget.

        Args:
            splitter_name: Identifier for the splitter
            splitter: The QSplitter widget
        """
        sizes = splitter.sizes()
        self.save_splitter_state(splitter_name, sizes)

    def restore_splitter_to_widget(self, splitter_name: str, splitter: QSplitter):
        """
        Restore splitter state directly to a QSplitter widget.

        Args:
            splitter_name: Identifier for the splitter
            splitter: The QSplitter widget
        """
        try:
            saved_state = self.get_splitter_state(splitter_name)
            if saved_state:
                if splitter_name == "notes_tag_panel":
                    # For tag panel, saved_state is a single value
                    scaling_helper = get_scaling_helper()
                    # Ensure saved_state is an int, not a list
                    # Ensure saved_state is an int, not a list
                    width_value = saved_state if isinstance(saved_state, int) else saved_state[0]
                    scaled_width = scaling_helper.scaled_size(width_value)
                    # Get current sizes and update first panel
                    current_sizes = splitter.sizes()
                    if len(current_sizes) >= 2:
                        remaining = sum(current_sizes) - scaled_width
                        splitter.setSizes([scaled_width, remaining])
                else:
                    # For percentage-based splitters
                    # Get total size based on orientation
                    try:
                        # type: ignore[attr-defined]
                        orientation_horizontal = Qt.Orientation.Horizontal
                    except AttributeError:
                        orientation_horizontal = 1
                    if splitter.orientation() == orientation_horizontal:
                        total_size = splitter.width()
                    else:
                        total_size = splitter.height()
                    # Convert percentages to actual sizes
                    sizes = [int(total_size * pct / 100) for pct in saved_state]
                    splitter.setSizes(sizes)
                self.logger.info(f"Splitter state restored: {splitter_name}")
        except Exception as e:
            self.logger.error(f"Failed to restore splitter state: {e}")
            if error_aggregator:
                error_aggregator.record_error(e, "restore_splitter_to_widget")


# Global instance for easy access
window_state_manager = WindowStateManager()

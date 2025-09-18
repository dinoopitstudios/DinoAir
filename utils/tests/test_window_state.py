"""Comprehensive tests for utils.window_state module."""

import json
import os
from unittest.mock import Mock, mock_open, patch

import pytest

from utils.window_state import WindowStateManager, window_state_manager


class TestWindowStateManager:
    """Tests for WindowStateManager class."""

    def test_window_state_manager_initialization(self):
        """Test WindowStateManager initialization."""
        with patch("utils.window_state.Logger") as mock_logger:
            manager = WindowStateManager()

            if manager.config_dir != "config":
                raise AssertionError
            if manager.state_file != os.path.join("config", "window_state.json"):
                raise AssertionError
            assert isinstance(manager.state_data, dict)
            mock_logger.assert_called_once()

    @patch("os.path.exists")
    @patch("os.makedirs")
    def test_ensure_config_dir_creation(self, mock_makedirs, mock_exists):
        """Test config directory creation."""
        mock_exists.return_value = False

        with patch("utils.window_state.Logger"):
            WindowStateManager()

            mock_makedirs.assert_called_once_with("config")

    @patch("os.path.exists")
    @patch("os.makedirs")
    def test_ensure_config_dir_creation_error(self, mock_makedirs, mock_exists):
        """Test config directory creation with error."""
        mock_exists.return_value = False
        mock_makedirs.side_effect = OSError("Permission denied")

        with patch("utils.window_state.Logger") as mock_logger:
            mock_logger_instance = Mock()
            mock_logger.return_value = mock_logger_instance

            WindowStateManager()

            mock_logger_instance.error.assert_called()

    @patch("os.path.exists")
    def test_load_state_no_file(self, mock_exists):
        """Test loading state when no file exists."""
        mock_exists.return_value = False

        with patch("utils.window_state.Logger"):
            manager = WindowStateManager()

            # Should return default state
            if "window" not in manager.state_data:
                raise AssertionError
            if "splitters" not in manager.state_data:
                raise AssertionError
            if manager.state_data["window"]["geometry"] != [100, 100, 1200, 800]:
                raise AssertionError
            if manager.state_data["window"]["maximized"] is not False:
                raise AssertionError

    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_load_state_with_file(self, mock_file, mock_exists):
        """Test loading state from existing file."""
        mock_exists.return_value = True
        test_state = {
            "window": {
                "geometry": [200, 200, 1400, 900],
                "maximized": True,
                "zoom_level": 1.2,
            },
            "splitters": {
                "main_bottom": [60, 40],
                "notes_content": [25, 75],
            },
        }
        mock_file.return_value.read.return_value = json.dumps(test_state)

        with patch("utils.window_state.Logger"), patch("json.load", return_value=test_state):
            manager = WindowStateManager()

            if manager.state_data["window"]["geometry"] != [200, 200, 1400, 900]:
                raise AssertionError
            if manager.state_data["window"]["maximized"] is not True:
                raise AssertionError
            if manager.state_data["window"]["zoom_level"] != 1.2:
                raise AssertionError

    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_load_state_partial_data(self, mock_file, mock_exists):
        """Test loading state with partial data (missing keys)."""
        mock_exists.return_value = True
        partial_state = {
            "window": {
                "geometry": [300, 300, 1000, 600],
                # Missing maximized and zoom_level
            },
            # Missing splitters entirely
        }

        with patch("utils.window_state.Logger"), patch("json.load", return_value=partial_state):
            manager = WindowStateManager()

            # Should merge with defaults
            if manager.state_data["window"]["geometry"] != [300, 300, 1000, 600]:
                raise AssertionError
            if manager.state_data["window"]["maximized"] is not False:
                raise AssertionError
            if "splitters" not in manager.state_data:
                raise AssertionError

    def test_save_window_state(self):
        """Test saving window state from widget."""
        mock_window = Mock()
        mock_geometry = Mock()
        mock_geometry.x.return_value = 150
        mock_geometry.y.return_value = 150
        mock_geometry.width.return_value = 1300
        mock_geometry.height.return_value = 850
        mock_window.geometry.return_value = mock_geometry
        mock_window.isMaximized.return_value = True

        with (
            patch("utils.window_state.Logger"),
            patch.object(WindowStateManager, "_save_state") as mock_save,
        ):
            manager = WindowStateManager()
            manager.save_window_state(mock_window)

            # Verify state was updated
            if manager.state_data["window"]["geometry"] != [150, 150, 1300, 850]:
                raise AssertionError
            if manager.state_data["window"]["maximized"] is not True:
                raise AssertionError
            mock_save.assert_called_once()

    def test_restore_window_state(self):
        """Test restoring window state to widget."""
        mock_window = Mock()

        with patch("utils.window_state.Logger"):
            manager = WindowStateManager()
            manager.state_data["window"]["geometry"] = [250, 250, 1100, 700]
            manager.state_data["window"]["maximized"] = False

            manager.restore_window_state(mock_window)

            # Verify geometry was set
            mock_window.setGeometry.assert_called_once_with(250, 250, 1100, 700)
            mock_window.showMaximized.assert_not_called()

    def test_restore_window_state_maximized(self):
        """Test restoring maximized window state."""
        mock_window = Mock()

        with patch("utils.window_state.Logger"):
            manager = WindowStateManager()
            manager.state_data["window"]["maximized"] = True

            manager.restore_window_state(mock_window)

            mock_window.showMaximized.assert_called_once()

    def test_save_zoom_level(self):
        """Test saving zoom level."""
        with (
            patch("utils.window_state.Logger"),
            patch.object(WindowStateManager, "_save_state") as mock_save,
        ):
            manager = WindowStateManager()
            manager.save_zoom_level(1.5)

            if manager.state_data["window"]["zoom_level"] != 1.5:
                raise AssertionError
            mock_save.assert_called_once()

    def test_get_zoom_level(self):
        """Test getting zoom level."""
        with patch("utils.window_state.Logger"):
            manager = WindowStateManager()
            manager.state_data["window"]["zoom_level"] = 1.3

            zoom_level = manager.get_zoom_level()
            if zoom_level != 1.3:
                raise AssertionError

    def test_get_zoom_level_default(self):
        """Test getting zoom level with default value."""
        with patch("utils.window_state.Logger"):
            manager = WindowStateManager()
            del manager.state_data["window"]["zoom_level"]  # Remove zoom level

            zoom_level = manager.get_zoom_level()
            if zoom_level != 1.0:
                raise AssertionError

    def test_save_splitter_state(self):
        """Test saving splitter state."""
        with (
            patch("utils.window_state.Logger"),
            patch.object(WindowStateManager, "_save_state") as mock_save,
        ):
            manager = WindowStateManager()
            manager.save_splitter_state("test_splitter", [400, 600])

            if manager.state_data["splitters"]["test_splitter"] != [400, 600]:
                raise AssertionError
            mock_save.assert_called_once()

    def test_get_splitter_state(self):
        """Test getting splitter state."""
        with patch("utils.window_state.Logger"):
            manager = WindowStateManager()
            manager.state_data["splitters"]["test_splitter"] = [300, 700]

            sizes = manager.get_splitter_state("test_splitter")
            if sizes != [300, 700]:
                raise AssertionError

    def test_get_splitter_state_not_found(self):
        """Test getting splitter state that doesn't exist."""
        with patch("utils.window_state.Logger"):
            manager = WindowStateManager()

            sizes = manager.get_splitter_state("nonexistent_splitter")
            assert sizes is None

    def test_save_splitter_from_widget(self):
        """Test saving splitter state from widget."""
        mock_splitter = Mock()
        mock_splitter.sizes.return_value = [350, 650]

        with (
            patch("utils.window_state.Logger"),
            patch.object(WindowStateManager, "_save_state") as mock_save,
        ):
            manager = WindowStateManager()
            manager.save_splitter_from_widget("widget_splitter", mock_splitter)

            if manager.state_data["splitters"]["widget_splitter"] != [350, 650]:
                raise AssertionError
            mock_save.assert_called_once()

    @patch("utils.window_state.get_scaling_helper")
    def test_restore_splitter_to_widget_percentage(self, mock_scaling_helper):
        """Test restoring percentage-based splitter state to widget."""
        mock_splitter = Mock()
        mock_splitter.width.return_value = 1000
        mock_splitter.orientation.return_value = 1  # Horizontal

        mock_scaling = Mock()
        mock_scaling_helper.return_value = mock_scaling

        with patch("utils.window_state.Logger"):
            manager = WindowStateManager()
            manager.state_data["splitters"]["test_splitter"] = [70, 30]  # Percentages

            manager.restore_splitter_to_widget("test_splitter", mock_splitter)

            # Should calculate sizes from percentages
            mock_splitter.setSizes.assert_called_once()
            args = mock_splitter.setSizes.call_args[0][0]
            if args[0] != 700:
                raise AssertionError
            if args[1] != 300:
                raise AssertionError

    @patch("utils.window_state.get_scaling_helper")
    def test_restore_splitter_to_widget_width_based(self, mock_scaling_helper):
        """Test restoring width-based splitter state to widget."""
        mock_splitter = Mock()
        mock_splitter.sizes.return_value = [400, 600]

        mock_scaling = Mock()
        mock_scaling.scaled_size.return_value = 300  # Scaled width
        mock_scaling_helper.return_value = mock_scaling

        with patch("utils.window_state.Logger"):
            manager = WindowStateManager()
            manager.state_data["splitters"]["notes_tag_panel"] = 250  # Width value

            manager.restore_splitter_to_widget("notes_tag_panel", mock_splitter)

            # Should set scaled width and remaining space
            mock_scaling.scaled_size.assert_called_once_with(250)
            mock_splitter.setSizes.assert_called_once_with([300, 700])  # 300 + (1000-300)

    def test_restore_splitter_exception_handling(self):
        """Test splitter restoration with exception."""
        mock_splitter = Mock()
        mock_splitter.setSizes.side_effect = RuntimeError("Widget error")

        with patch("utils.window_state.Logger") as mock_logger:
            mock_logger_instance = Mock()
            mock_logger.return_value = mock_logger_instance

            manager = WindowStateManager()
            manager.state_data["splitters"]["test_splitter"] = [50, 50]

            # Should handle exception gracefully
            manager.restore_splitter_to_widget("test_splitter", mock_splitter)

            mock_logger_instance.error.assert_called()

    @patch("builtins.open", new_callable=mock_open)
    @patch("json.dump")
    @patch("os.path.exists")
    def test_save_state_success(self, mock_exists, mock_json_dump, mock_file):
        """Test successful state saving."""
        mock_exists.return_value = False  # No existing state file during init

        with patch("utils.window_state.Logger") as mock_logger:
            mock_logger_instance = Mock()
            mock_logger.return_value = mock_logger_instance

            manager = WindowStateManager()
            manager._save_state()

            mock_file.assert_called_once_with(manager.state_file, "w", encoding="utf-8")
            mock_json_dump.assert_called_once()
            mock_logger_instance.info.assert_called()

    @patch("builtins.open", new_callable=mock_open)
    def test_save_state_exception(self, mock_file):
        """Test state saving with exception."""
        mock_file.side_effect = OSError("Write error")

        with patch("utils.window_state.Logger") as mock_logger:
            mock_logger_instance = Mock()
            mock_logger.return_value = mock_logger_instance

            manager = WindowStateManager()
            manager._save_state()

            mock_logger_instance.error.assert_called()

    def test_window_state_error_handling(self):
        """Test window state operations with widget errors."""
        mock_window = Mock()
        mock_window.geometry.side_effect = RuntimeError("Widget error")

        with patch("utils.window_state.Logger") as mock_logger:
            mock_logger_instance = Mock()
            mock_logger.return_value = mock_logger_instance

            manager = WindowStateManager()
            manager.save_window_state(mock_window)

            # Should handle error gracefully
            mock_logger_instance.error.assert_called()


class TestGlobalInstance:
    """Tests for global window_state_manager instance."""

    def test_global_instance_exists(self):
        """Test that global instance is created."""
        assert window_state_manager is not None
        assert isinstance(window_state_manager, WindowStateManager)

    def test_global_instance_singleton_behavior(self):
        """Test that global instance behaves consistently."""
        # The global instance should maintain state
        window_state_manager.save_zoom_level(1.8)
        if window_state_manager.get_zoom_level() != 1.8:
            raise AssertionError


class TestSafeOperation:
    """Tests for safe_operation utility function."""

    @patch("utils.window_state.safe_operation")
    def test_safe_operation_success(self, mock_safe_op):
        """Test safe_operation with successful function."""
        mock_safe_op.return_value = {"test": "value"}

        with patch("utils.window_state.Logger"):
            WindowStateManager()

        # safe_operation should have been called during state loading
        mock_safe_op.assert_called()

    @patch("utils.window_state.safe_operation")
    def test_safe_operation_fallback(self, mock_safe_op):
        """Test safe_operation with fallback value."""
        default_state = {"window": {"geometry": [100, 100, 1200, 800]}}
        mock_safe_op.return_value = default_state

        with patch("utils.window_state.Logger"):
            WindowStateManager()

        mock_safe_op.assert_called()


class TestWindowStateIntegration:
    """Integration tests for window state management."""

    @pytest.mark.integration
    def test_complete_window_state_workflow(self):
        """Test complete window state save/restore workflow."""
        mock_window = Mock()

        # Setup window geometry
        mock_geometry = Mock()
        mock_geometry.x.return_value = 200
        mock_geometry.y.return_value = 300
        mock_geometry.width.return_value = 1400
        mock_geometry.height.return_value = 900
        mock_window.geometry.return_value = mock_geometry
        mock_window.isMaximized.return_value = False

        with (
            patch("utils.window_state.Logger"),
            patch.object(WindowStateManager, "_save_state") as mock_save,
        ):
            manager = WindowStateManager()

            # Save state
            manager.save_window_state(mock_window)
            manager.save_zoom_level(1.25)

            # Verify state was saved
            if manager.state_data["window"]["geometry"] != [200, 300, 1400, 900]:
                raise AssertionError
            if manager.state_data["window"]["zoom_level"] != 1.25:
                raise AssertionError
            if mock_save.call_count != 2:
                raise AssertionError

            # Restore state to new window
            new_window = Mock()
            manager.restore_window_state(new_window)

            new_window.setGeometry.assert_called_once_with(200, 300, 1400, 900)
            if manager.get_zoom_level() != 1.25:
                raise AssertionError

    @pytest.mark.integration
    def test_splitter_state_workflow(self):
        """Test complete splitter state save/restore workflow."""
        mock_splitter = Mock()
        mock_splitter.sizes.return_value = [600, 400]

        with (
            patch("utils.window_state.Logger"),
            patch.object(WindowStateManager, "_save_state") as mock_save,
            patch("utils.window_state.get_scaling_helper") as mock_scaling_helper,
        ):
            mock_scaling = Mock()
            mock_scaling_helper.return_value = mock_scaling

            manager = WindowStateManager()

            # Save splitter state
            manager.save_splitter_from_widget("main_splitter", mock_splitter)

            # Verify state was saved
            if manager.state_data["splitters"]["main_splitter"] != [600, 400]:
                raise AssertionError
            mock_save.assert_called_once()

            # Restore state to new splitter
            new_splitter = Mock()
            new_splitter.width.return_value = 1000
            new_splitter.orientation.return_value = 1

            manager.restore_splitter_to_widget("main_splitter", new_splitter)

            new_splitter.setSizes.assert_called_once()

    @pytest.mark.boundary
    def test_extreme_window_values(self):
        """Test window state with extreme values."""
        with patch("utils.window_state.Logger"), patch.object(WindowStateManager, "_save_state"):
            manager = WindowStateManager()

            # Test extreme zoom levels
            manager.save_zoom_level(0.1)  # Very small
            if manager.get_zoom_level() != 0.1:
                raise AssertionError

            manager.save_zoom_level(10.0)  # Very large
            if manager.get_zoom_level() != 10.0:
                raise AssertionError

            # Test extreme window geometry
            extreme_geometry = [-1000, -1000, 5000, 5000]
            manager.state_data["window"]["geometry"] = extreme_geometry

            mock_window = Mock()
            manager.restore_window_state(mock_window)

            mock_window.setGeometry.assert_called_once_with(-1000, -1000, 5000, 5000)

    @pytest.mark.boundary
    def test_invalid_state_data_recovery(self):
        """Test recovery from invalid state data."""
        with patch("utils.window_state.Logger"):
            manager = WindowStateManager()

            # Corrupt state data
            manager.state_data = {"invalid": "data"}

            # Should handle gracefully
            zoom_level = manager.get_zoom_level()
            if zoom_level != 1.0:
                raise AssertionError

            splitter_state = manager.get_splitter_state("any_splitter")
            assert splitter_state is None

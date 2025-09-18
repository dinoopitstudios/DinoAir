"""Comprehensive tests for utils.scaling module."""

from unittest.mock import Mock, patch

import pytest

from utils.scaling import ScalingHelper, get_scaling_helper


class TestScalingHelper:
    """Tests for ScalingHelper class."""

    def test_scaling_helper_initialization(self):
        """Test ScalingHelper initialization."""
        helper = ScalingHelper()

        assert helper._scale_factor is None
        assert helper._font_metrics is None
        assert helper._zoom_level == ScalingHelper.DEFAULT_ZOOM
        assert helper.logger.name == "utils.scaling"

    def test_scaling_helper_constants(self):
        """Test ScalingHelper constants are defined and of correct type."""
        assert isinstance(ScalingHelper.BASELINE_DPI, int | float)
        assert isinstance(ScalingHelper.MIN_ZOOM, int | float)
        assert isinstance(ScalingHelper.MAX_ZOOM, int | float)
        assert isinstance(ScalingHelper.DEFAULT_ZOOM, int | float)
        assert isinstance(ScalingHelper.ZOOM_STEP, int | float)

    @patch("utils.scaling.QApplication")
    def test_get_scale_factor_no_app(self, mock_qapp):
        """Test get_scale_factor when no QApplication instance exists."""
        mock_qapp.instance.return_value = None

        helper = ScalingHelper()
        scale_factor = helper.get_scale_factor()

        assert scale_factor == 1.0
        assert helper._scale_factor == 1.0

    @patch("utils.scaling.QApplication")
    def test_get_scale_factor_with_app(self, mock_qapp):
        """Test get_scale_factor with QApplication instance."""
        # Mock the app and screen
        mock_app = Mock()
        mock_screen = Mock()
        mock_screen.logicalDotsPerInch.return_value = 144  # 150% scaling
        mock_app.primaryScreen.return_value = mock_screen
        mock_qapp.instance.return_value = mock_app

        helper = ScalingHelper()
        scale_factor = helper.get_scale_factor()

        expected_scale = 144 / ScalingHelper.BASELINE_DPI
        assert scale_factor == expected_scale
        assert helper._scale_factor == expected_scale

    @patch("utils.scaling.QApplication")
    def test_get_scale_factor_exception_handling(self, mock_qapp):
        """Test get_scale_factor with exception handling."""
        # Mock app to raise exception
        mock_app = Mock()
        mock_app.primaryScreen.side_effect = Exception("Screen error")
        mock_qapp.instance.return_value = mock_app

        helper = ScalingHelper()
        scale_factor = helper.get_scale_factor()

        assert scale_factor == 1.0

    def test_set_zoom_level_valid(self):
        """Test setting valid zoom levels."""
        helper = ScalingHelper()

        helper.set_zoom_level(1.5)
        assert helper._zoom_level == 1.5

        helper.set_zoom_level(ScalingHelper.MIN_ZOOM)
        assert helper._zoom_level == ScalingHelper.MIN_ZOOM

        helper.set_zoom_level(ScalingHelper.MAX_ZOOM)
        assert helper._zoom_level == ScalingHelper.MAX_ZOOM

    def test_set_zoom_level_clamping(self):
        """Test zoom level clamping to valid range."""
        helper = ScalingHelper()

        # Test below minimum
        helper.set_zoom_level(0.3)
        assert helper._zoom_level == ScalingHelper.MIN_ZOOM

        # Test above maximum
        helper.set_zoom_level(5.0)
        assert helper._zoom_level == ScalingHelper.MAX_ZOOM

    def test_get_current_zoom_level(self):
        """Test getting current zoom level."""
        helper = ScalingHelper()

        assert helper.get_current_zoom_level() == ScalingHelper.DEFAULT_ZOOM

        helper.set_zoom_level(1.2)
        assert helper.get_current_zoom_level() == 1.2

    @patch("utils.scaling.QApplication")
    def test_scaled_font_size(self, mock_qapp):
        """Test scaled font size calculation."""
        mock_qapp.instance.return_value = None  # No app, scale factor = 1.0

        helper = ScalingHelper()
        helper.set_zoom_level(1.2)

        # Base size 12, scale factor 1.0, zoom 1.2 = 12 * 1.0 * 1.2 = 14.4 -> 14
        scaled_size = helper.scaled_font_size(12)
        assert scaled_size == 14

    @patch("utils.scaling.QApplication")
    def test_scaled_size(self, mock_qapp):
        """Test scaled size calculation."""
        mock_qapp.instance.return_value = None  # No app, scale factor = 1.0

        helper = ScalingHelper()
        helper.set_zoom_level(1.5)

        # Base size 100, scale factor 1.0, zoom 1.5 = 100 * 1.0 * 1.5 = 150
        scaled_size = helper.scaled_size(100)
        assert scaled_size == 150

    @patch("utils.scaling.QApplication")
    @patch("utils.scaling.QFontMetrics")
    def test_get_font_metrics_no_font(self, mock_font_metrics, mock_qapp):
        """Test get_font_metrics with no font specified."""
        mock_app = Mock()
        mock_app_font = Mock()
        mock_app.font.return_value = mock_app_font
        mock_qapp.instance.return_value = mock_app
        mock_font_metrics_instance = Mock()
        mock_font_metrics.return_value = mock_font_metrics_instance

        helper = ScalingHelper()
        metrics = helper.get_font_metrics()

        assert metrics == mock_font_metrics_instance
        mock_font_metrics.assert_called_once_with(mock_app_font)

    @patch("utils.scaling.QFontMetrics")
    def test_get_font_metrics_with_font(self, mock_font_metrics):
        """Test get_font_metrics with specific font."""
        mock_font = Mock()
        mock_font_metrics_instance = Mock()
        mock_font_metrics.return_value = mock_font_metrics_instance

        helper = ScalingHelper()
        metrics = helper.get_font_metrics(mock_font)

        assert metrics == mock_font_metrics_instance
        mock_font_metrics.assert_called_once_with(mock_font)

    def test_reset_cache(self):
        """Test cache reset functionality."""
        helper = ScalingHelper()
        helper._scale_factor = 1.5
        helper._font_metrics = Mock()

        helper.reset_cache()

        assert helper._scale_factor is None
        assert helper._font_metrics is None

    def test_zoom_in(self):
        """Test zoom in functionality."""
        helper = ScalingHelper()
        initial_zoom = helper._zoom_level

        helper.zoom_in()

        expected_zoom = min(initial_zoom + ScalingHelper.ZOOM_STEP, ScalingHelper.MAX_ZOOM)
        assert helper._zoom_level == expected_zoom

    def test_zoom_out(self):
        """Test zoom out functionality."""
        helper = ScalingHelper()
        helper.set_zoom_level(1.5)  # Set higher zoom level

        helper.zoom_out()

        expected_zoom = max(1.5 - ScalingHelper.ZOOM_STEP, ScalingHelper.MIN_ZOOM)
        assert helper._zoom_level == expected_zoom

    def test_reset_zoom(self):
        """Test zoom reset functionality."""
        helper = ScalingHelper()
        helper.set_zoom_level(2.0)

        helper.reset_zoom()

        assert helper._zoom_level == ScalingHelper.DEFAULT_ZOOM

    @patch("utils.scaling.QApplication")
    def test_get_font_scale(self, mock_qapp):
        """Test get_font_scale method."""
        mock_qapp.instance.return_value = None  # No app, scale factor = 1.0

        helper = ScalingHelper()
        helper.set_zoom_level(1.2)

        scale_info = helper.get_font_scale()

        assert "small" in scale_info
        assert "normal" in scale_info
        assert "large" in scale_info
        assert "title" in scale_info

        # Should be scaled by zoom level (1.2)
        assert scale_info["normal"] == int(12 * 1.2)

    @patch("utils.scaling.QApplication")
    def test_get_dpi_scale(self, mock_qapp):
        """Test get_dpi_scale method."""
        mock_qapp.instance.return_value = None  # No app, scale factor = 1.0

        helper = ScalingHelper()
        dpi_scale = helper.get_dpi_scale()

        assert dpi_scale == 1.0

    @patch("utils.scaling.QApplication")
    def test_get_font_for_role(self, mock_qapp):
        """Test get_font_for_role method."""
        mock_qapp.instance.return_value = None  # No app, scale factor = 1.0

        helper = ScalingHelper()
        helper.set_zoom_level(1.5)

        # Test different font roles
        small_font = helper.get_font_for_role("small")
        normal_font = helper.get_font_for_role("normal")
        large_font = helper.get_font_for_role("large")
        title_font = helper.get_font_for_role("title")

        assert small_font < normal_font < large_font < title_font

        # Test unknown role returns normal
        unknown_font = helper.get_font_for_role("unknown")
        assert unknown_font == normal_font

    def test_zoom_level_signal_emission(self):
        """Test that zoom_changed signal is emitted when zoom level changes."""
        helper = ScalingHelper()

        # Mock the signal
        helper.zoom_changed = Mock()

        helper.set_zoom_level(1.5)
        helper.zoom_changed.emit.assert_called_once_with(1.5)

    def test_zoom_level_no_signal_when_same(self):
        """Test that zoom_changed signal is not emitted when zoom level doesn't change."""
        helper = ScalingHelper()
        helper.zoom_changed = Mock()

        # Set to current zoom level
        helper.set_zoom_level(ScalingHelper.DEFAULT_ZOOM)

        # Signal should not be emitted since zoom didn't change
        helper.zoom_changed.emit.assert_not_called()

    @patch("utils.scaling.QApplication")
    def test_complex_scaling_scenario(self, mock_qapp):
        """Test complex scaling scenario with high DPI and zoom."""
        # Mock high DPI display
        mock_app = Mock()
        mock_screen = Mock()
        mock_screen.logicalDotsPerInch.return_value = 192  # 200% DPI scaling
        mock_app.primaryScreen.return_value = mock_screen
        mock_qapp.instance.return_value = mock_app

        helper = ScalingHelper()
        helper.set_zoom_level(1.5)  # Additional 150% user zoom

        # Should combine DPI scaling (2.0) with user zoom (1.5)
        scale_factor = helper.get_scale_factor()
        assert scale_factor == 2.0  # 192/96

        # Font size should be scaled by both
        base_font_size = 12
        scaled_font = helper.scaled_font_size(base_font_size)
        expected = int(base_font_size * scale_factor * 1.5)  # 12 * 2.0 * 1.5 = 36
        assert scaled_font == expected


class TestGetScalingHelper:
    """Tests for get_scaling_helper global function."""

    def test_get_scaling_helper_singleton(self):
        """Test that get_scaling_helper returns the same instance."""
        helper1 = get_scaling_helper()
        helper2 = get_scaling_helper()

        assert helper1 is helper2
        assert isinstance(helper1, ScalingHelper)

    def test_get_scaling_helper_initialization(self):
        """Test that get_scaling_helper returns properly initialized instance."""
        helper = get_scaling_helper()

        assert helper._zoom_level == ScalingHelper.DEFAULT_ZOOM
        assert helper._scale_factor is None
        assert helper._font_metrics is None


class TestScalingHelperIntegration:
    """Integration tests for ScalingHelper."""

    @pytest.mark.integration
    @patch("utils.scaling.QApplication")
    def test_zoom_workflow(self, mock_qapp):
        """Test complete zoom workflow."""
        mock_qapp.instance.return_value = None

        helper = ScalingHelper()

        # Start with default zoom
        assert helper.get_current_zoom_level() == 1.0

        # Zoom in several times
        helper.zoom_in()
        helper.zoom_in()
        helper.zoom_in()

        expected_zoom = min(1.0 + 3 * ScalingHelper.ZOOM_STEP, ScalingHelper.MAX_ZOOM)
        assert helper.get_current_zoom_level() == expected_zoom

        # Reset zoom
        helper.reset_zoom()
        assert helper.get_current_zoom_level() == 1.0

        # Zoom out from default (should clamp to minimum)
        helper.zoom_out()
        assert helper.get_current_zoom_level() >= ScalingHelper.MIN_ZOOM

    @pytest.mark.boundary
    @patch("utils.scaling.QApplication")
    def test_extreme_dpi_values(self, mock_qapp):
        """Test handling of extreme DPI values."""
        # Test very low DPI
        mock_app = Mock()
        mock_screen = Mock()
        mock_screen.logicalDotsPerInch.return_value = 48  # Very low DPI
        mock_app.primaryScreen.return_value = mock_screen
        mock_qapp.instance.return_value = mock_app

        helper = ScalingHelper()
        scale_factor = helper.get_scale_factor()
        assert scale_factor == 0.5  # 48/96

        # Test very high DPI
        mock_screen.logicalDotsPerInch.return_value = 480  # Very high DPI
        helper.reset_cache()  # Clear cached value
        scale_factor = helper.get_scale_factor()
        assert scale_factor == 5.0  # 480/96

    @pytest.mark.boundary
    def test_zoom_boundary_conditions(self):
        """Test zoom level boundary conditions."""
        helper = ScalingHelper()

        # Test setting zoom to exact boundaries
        helper.set_zoom_level(ScalingHelper.MIN_ZOOM)
        assert helper.get_current_zoom_level() == ScalingHelper.MIN_ZOOM

        helper.set_zoom_level(ScalingHelper.MAX_ZOOM)
        assert helper.get_current_zoom_level() == ScalingHelper.MAX_ZOOM

        # Test zooming beyond boundaries
        helper.set_zoom_level(ScalingHelper.MAX_ZOOM)
        helper.zoom_in()  # Should not exceed maximum
        assert helper.get_current_zoom_level() == ScalingHelper.MAX_ZOOM

        helper.set_zoom_level(ScalingHelper.MIN_ZOOM)
        helper.zoom_out()  # Should not go below minimum
        assert helper.get_current_zoom_level() == ScalingHelper.MIN_ZOOM

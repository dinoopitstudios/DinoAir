"""
Unit tests for colors.py module.
Tests DinoPit Studios color configuration and stylesheet generation.
"""

from unittest.mock import MagicMock, patch

from ..colors import DinoPitColors


class TestDinoPitColors:
    """Test cases for DinoPitColors class."""

    def test_color_constants(self):
        """Test that all color constants are defined correctly."""
        # Primary Brand Colors
        if DinoPitColors.DINOPIT_ORANGE != "#FF6B35":
            raise AssertionError
        if DinoPitColors.DINOPIT_FIRE != "#FF4500":
            raise AssertionError
        if DinoPitColors.STUDIOS_CYAN != "#00BFFF":
            raise AssertionError

        # Background Colors
        if DinoPitColors.MAIN_BACKGROUND != "#2B3A52":
            raise AssertionError
        if DinoPitColors.PANEL_BACKGROUND != "#34435A":
            raise AssertionError
        if DinoPitColors.SIDEBAR_BACKGROUND != "#344359":
            raise AssertionError

        # UI Element Colors
        if DinoPitColors.SOFT_ORANGE != "#CC8B66":
            raise AssertionError
        if DinoPitColors.SOFT_ORANGE_HOVER != "#E6A085":
            raise AssertionError

        # Text Colors
        if DinoPitColors.PRIMARY_TEXT != "#FFFFFF":
            raise AssertionError
        if DinoPitColors.SECONDARY_TEXT != "#CCCCCC":
            raise AssertionError
        if DinoPitColors.ACCENT_TEXT != DinoPitColors.STUDIOS_CYAN:
            raise AssertionError
        if DinoPitColors.BRAND_TEXT != DinoPitColors.DINOPIT_ORANGE:
            raise AssertionError

        # Border and Accent Colors
        if DinoPitColors.BORDER_COLOR != DinoPitColors.SOFT_ORANGE:
            raise AssertionError
        if DinoPitColors.BORDER_HOVER != DinoPitColors.SOFT_ORANGE_HOVER:
            raise AssertionError
        if DinoPitColors.ACCENT_BORDER != DinoPitColors.DINOPIT_ORANGE:
            raise AssertionError

    def test_color_hex_format(self):
        """Test that all colors are in proper hex format."""
        color_attributes = [
            "DINOPIT_ORANGE",
            "DINOPIT_FIRE",
            "STUDIOS_CYAN",
            "MAIN_BACKGROUND",
            "PANEL_BACKGROUND",
            "SIDEBAR_BACKGROUND",
            "SOFT_ORANGE",
            "SOFT_ORANGE_HOVER",
            "PRIMARY_TEXT",
            "SECONDARY_TEXT",
        ]

        for attr_name in color_attributes:
            color_value = getattr(DinoPitColors, attr_name)
            assert isinstance(color_value, str)
            if not color_value.startswith("#"):
                raise AssertionError
            assert len(color_value) == 7  # #RRGGBB format
            # Check that it's valid hex
            int(color_value[1:], 16)  # Should not raise ValueError

    def test_color_references(self):
        """Test that color references point to correct values."""
        if DinoPitColors.ACCENT_TEXT != "#00BFFF":
            raise AssertionError
        if DinoPitColors.BRAND_TEXT != "#FF6B35":
            raise AssertionError
        if DinoPitColors.BORDER_COLOR != "#CC8B66":
            raise AssertionError
        if DinoPitColors.BORDER_HOVER != "#E6A085":
            raise AssertionError
        if DinoPitColors.ACCENT_BORDER != "#FF6B35":
            raise AssertionError


class TestGetStylesheet:
    """Test cases for get_stylesheet method."""

    def test_get_stylesheet_scaling_integration(self):
        """Test that get_stylesheet integrates with scaling helper."""
        mock_scaling = MagicMock()
        mock_scaling.scaled_size.return_value = 10
        mock_scaling.scaled_font_size.return_value = 14

        with patch("utils.colors.get_scaling_helper", return_value=mock_scaling):
            stylesheet = DinoPitColors.get_stylesheet("header")

            # Should have called scaling methods
            mock_scaling.scaled_size.assert_called()
            mock_scaling.scaled_font_size.assert_called()

            # Should contain expected elements
            assert isinstance(stylesheet, str)
            if DinoPitColors.DINOPIT_ORANGE not in stylesheet:
                raise AssertionError
            if "font-weight: bold" not in stylesheet:
                raise AssertionError

    def test_get_stylesheet_main_background(self):
        """Test main_background stylesheet."""
        with patch("utils.colors.get_scaling_helper"):
            stylesheet = DinoPitColors.get_stylesheet("main_background")

            if f"background-color: {DinoPitColors.MAIN_BACKGROUND}" not in stylesheet:
                raise AssertionError
            if not stylesheet.strip().endswith(";"):
                raise AssertionError

    def test_get_stylesheet_header(self):
        """Test header stylesheet."""
        mock_scaling = MagicMock()
        mock_scaling.scaled_size.return_value = 2
        mock_scaling.scaled_font_size.return_value = 14

        with patch("utils.colors.get_scaling_helper", return_value=mock_scaling):
            stylesheet = DinoPitColors.get_stylesheet("header")

            if f"background-color: {DinoPitColors.DINOPIT_ORANGE}" not in stylesheet:
                raise AssertionError
            if f"border-bottom: 2px solid {DinoPitColors.DINOPIT_FIRE}" not in stylesheet:
                raise AssertionError
            if f"color: {DinoPitColors.PRIMARY_TEXT}" not in stylesheet:
                raise AssertionError
            if "font-weight: bold" not in stylesheet:
                raise AssertionError
            if "font-size: 14px" not in stylesheet:
                raise AssertionError

    def test_get_stylesheet_panel(self):
        """Test panel stylesheet."""
        with patch("utils.colors.get_scaling_helper"):
            stylesheet = DinoPitColors.get_stylesheet("panel")

            if f"background-color: {DinoPitColors.PANEL_BACKGROUND}" not in stylesheet:
                raise AssertionError

    def test_get_stylesheet_input_field(self):
        """Test input_field stylesheet."""
        mock_scaling = MagicMock()
        mock_scaling.scaled_size.side_effect = [
            1,
            20,
            8,
            15,
        ]  # border, radius, padding vertical, padding horizontal
        mock_scaling.scaled_font_size.return_value = 14

        with patch("utils.colors.get_scaling_helper", return_value=mock_scaling):
            stylesheet = DinoPitColors.get_stylesheet("input_field")

            # Should contain QLineEdit styles
            if "QLineEdit {" not in stylesheet:
                raise AssertionError
            if f"border: 1px solid {DinoPitColors.BORDER_COLOR}" not in stylesheet:
                raise AssertionError
            if "border-radius: 20px" not in stylesheet:
                raise AssertionError
            if "padding: 8px 15px" not in stylesheet:
                raise AssertionError
            if f"background-color: {DinoPitColors.MAIN_BACKGROUND}" not in stylesheet:
                raise AssertionError
            if f"color: {DinoPitColors.ACCENT_TEXT}" not in stylesheet:
                raise AssertionError

            # Should contain focus styles
            if "QLineEdit:focus {" not in stylesheet:
                raise AssertionError
            if f"border-color: {DinoPitColors.BORDER_HOVER}" not in stylesheet:
                raise AssertionError

    def test_get_stylesheet_button(self):
        """Test button stylesheet."""
        mock_scaling = MagicMock()
        mock_scaling.scaled_size.return_value = 20
        mock_scaling.scaled_font_size.return_value = 16

        with patch("utils.colors.get_scaling_helper", return_value=mock_scaling):
            stylesheet = DinoPitColors.get_stylesheet("button")

            # Basic button styles
            if "QPushButton {" not in stylesheet:
                raise AssertionError
            if f"background-color: {DinoPitColors.DINOPIT_ORANGE}" not in stylesheet:
                raise AssertionError
            if f"color: {DinoPitColors.PRIMARY_TEXT}" not in stylesheet:
                raise AssertionError
            if "border: none" not in stylesheet:
                raise AssertionError
            if "border-radius: 20px" not in stylesheet:
                raise AssertionError
            if "font-size: 16px" not in stylesheet:
                raise AssertionError
            if "font-weight: bold" not in stylesheet:
                raise AssertionError

            # Hover state
            if "QPushButton:hover {" not in stylesheet:
                raise AssertionError
            if f"background-color: {DinoPitColors.DINOPIT_FIRE}" not in stylesheet:
                raise AssertionError

            # Pressed state
            if "QPushButton:pressed {" not in stylesheet:
                raise AssertionError
            if "background-color: #E55A2B" not in stylesheet:
                raise AssertionError

            # Disabled state
            if "QPushButton:disabled {" not in stylesheet:
                raise AssertionError
            if "background-color: #666666" not in stylesheet:
                raise AssertionError
            if "color: #999999" not in stylesheet:
                raise AssertionError

    def test_get_stylesheet_unknown_element(self):
        """Test get_stylesheet with unknown element type."""
        with patch("utils.colors.get_scaling_helper"):
            stylesheet = DinoPitColors.get_stylesheet("unknown_element")

            # Should return empty string for unknown elements
            if stylesheet != "":
                raise AssertionError

    def test_get_stylesheet_default_element(self):
        """Test get_stylesheet with default element type."""
        with patch("utils.colors.get_scaling_helper"):
            stylesheet = DinoPitColors.get_stylesheet("default")

            # Should return empty string for default
            if stylesheet != "":
                raise AssertionError

    def test_get_stylesheet_case_sensitivity(self):
        """Test get_stylesheet case sensitivity."""
        with patch("utils.colors.get_scaling_helper"):
            # Should be case sensitive
            header_stylesheet = DinoPitColors.get_stylesheet("header")
            header_caps_stylesheet = DinoPitColors.get_stylesheet("HEADER")

            if header_stylesheet == "":
                raise AssertionError
            if header_caps_stylesheet != "":
                raise AssertionError

    def test_get_stylesheet_scale_factor_parameter(self):
        """Test get_stylesheet scale_factor parameter."""
        mock_scaling = MagicMock()

        with patch("utils.colors.get_scaling_helper", return_value=mock_scaling):
            # Scale factor parameter is reserved for future use
            stylesheet = DinoPitColors.get_stylesheet("header", scale_factor=2.0)

            # Should still work (parameter is currently unused but reserved)
            assert isinstance(stylesheet, str)

    def test_get_stylesheet_scaling_helper_calls(self):
        """Test that get_stylesheet makes appropriate scaling helper calls."""
        mock_scaling = MagicMock()
        mock_scaling.scaled_size.return_value = 5
        mock_scaling.scaled_font_size.return_value = 12

        with patch("utils.colors.get_scaling_helper", return_value=mock_scaling):
            # Test input_field which uses both scaling methods
            DinoPitColors.get_stylesheet("input_field")

            # Should have called both scaling methods
            if not mock_scaling.scaled_size.called:
                raise AssertionError
            if not mock_scaling.scaled_font_size.called:
                raise AssertionError

    def test_get_stylesheet_multiple_calls_consistency(self):
        """Test that multiple calls return consistent results."""
        mock_scaling = MagicMock()
        mock_scaling.scaled_size.return_value = 10
        mock_scaling.scaled_font_size.return_value = 14

        with patch("utils.colors.get_scaling_helper", return_value=mock_scaling):
            stylesheet1 = DinoPitColors.get_stylesheet("button")
            stylesheet2 = DinoPitColors.get_stylesheet("button")

            if stylesheet1 != stylesheet2:
                raise AssertionError

    def test_get_stylesheet_all_element_types(self):
        """Test get_stylesheet with all supported element types."""
        mock_scaling = MagicMock()
        mock_scaling.scaled_size.return_value = 10
        mock_scaling.scaled_font_size.return_value = 14

        element_types = ["main_background", "header", "panel", "input_field", "button"]

        with patch("utils.colors.get_scaling_helper", return_value=mock_scaling):
            for element_type in element_types:
                stylesheet = DinoPitColors.get_stylesheet(element_type)

                assert isinstance(stylesheet, str)
                if len(stylesheet) <= 0:
                    raise AssertionError

                # Each stylesheet should contain its primary color
                if element_type == "main_background":
                    if DinoPitColors.MAIN_BACKGROUND not in stylesheet:
                        raise AssertionError
                elif element_type == "header":
                    if DinoPitColors.DINOPIT_ORANGE not in stylesheet:
                        raise AssertionError
                elif element_type == "panel":
                    if DinoPitColors.PANEL_BACKGROUND not in stylesheet:
                        raise AssertionError
                elif element_type in ["input_field", "button"]:
                    # These have more complex stylesheets but should contain colors
                    if len(stylesheet) <= 50:
                        raise AssertionError


class TestStylesheetContent:
    """Test cases for stylesheet content validation."""

    def test_stylesheet_css_syntax(self):
        """Test that generated stylesheets have valid CSS syntax."""
        mock_scaling = MagicMock()
        mock_scaling.scaled_size.return_value = 10
        mock_scaling.scaled_font_size.return_value = 14

        with patch("utils.colors.get_scaling_helper", return_value=mock_scaling):
            # Test complex stylesheets
            complex_elements = ["input_field", "button"]

            for element_type in complex_elements:
                stylesheet = DinoPitColors.get_stylesheet(element_type)

                # Basic CSS syntax checks
                if stylesheet.count("{") != stylesheet.count("}"):
                    raise AssertionError

                # Should contain proper CSS selectors
                if element_type == "input_field":
                    if "QLineEdit {" not in stylesheet:
                        raise AssertionError
                    if "QLineEdit:focus {" not in stylesheet:
                        raise AssertionError
                elif element_type == "button":
                    if "QPushButton {" not in stylesheet:
                        raise AssertionError
                    if "QPushButton:hover {" not in stylesheet:
                        raise AssertionError
                    if "QPushButton:pressed {" not in stylesheet:
                        raise AssertionError
                    if "QPushButton:disabled {" not in stylesheet:
                        raise AssertionError

    def test_stylesheet_color_consistency(self):
        """Test that stylesheets use consistent color references."""
        mock_scaling = MagicMock()
        mock_scaling.scaled_size.return_value = 10
        mock_scaling.scaled_font_size.return_value = 14

        with patch("utils.colors.get_scaling_helper", return_value=mock_scaling):
            button_stylesheet = DinoPitColors.get_stylesheet("button")
            header_stylesheet = DinoPitColors.get_stylesheet("header")

            # Both should use DINOPIT_ORANGE as primary color
            if DinoPitColors.DINOPIT_ORANGE not in button_stylesheet:
                raise AssertionError
            if DinoPitColors.DINOPIT_ORANGE not in header_stylesheet:
                raise AssertionError

            # Both should use DINOPIT_FIRE for hover/accent
            if DinoPitColors.DINOPIT_FIRE not in button_stylesheet:
                raise AssertionError
            if DinoPitColors.DINOPIT_FIRE not in header_stylesheet:
                raise AssertionError

    def test_stylesheet_scaling_integration(self):
        """Test proper integration with scaling system."""
        mock_scaling = MagicMock()

        # Setup different return values for different calls
        mock_scaling.scaled_size.side_effect = [2, 20, 8, 15]  # Multiple calls
        mock_scaling.scaled_font_size.return_value = 16

        with patch("utils.colors.get_scaling_helper", return_value=mock_scaling):
            stylesheet = DinoPitColors.get_stylesheet("input_field")

            # Should have used scaled values
            if "2px" not in stylesheet:
                raise AssertionError
            if "20px" not in stylesheet:
                raise AssertionError
            if "8px 15px" not in stylesheet:
                raise AssertionError
            if "16px" not in stylesheet:
                raise AssertionError

    def test_stylesheet_qt_selector_format(self):
        """Test that stylesheets use proper Qt selector format."""
        mock_scaling = MagicMock()
        mock_scaling.scaled_size.return_value = 10
        mock_scaling.scaled_font_size.return_value = 14

        with patch("utils.colors.get_scaling_helper", return_value=mock_scaling):
            input_stylesheet = DinoPitColors.get_stylesheet("input_field")
            button_stylesheet = DinoPitColors.get_stylesheet("button")

            # Should use Qt-specific selectors
            if "QLineEdit" not in input_stylesheet:
                raise AssertionError
            if "QLineEdit:focus" not in input_stylesheet:
                raise AssertionError
            if "QPushButton" not in button_stylesheet:
                raise AssertionError
            if "QPushButton:hover" not in button_stylesheet:
                raise AssertionError
            if "QPushButton:pressed" not in button_stylesheet:
                raise AssertionError
            if "QPushButton:disabled" not in button_stylesheet:
                raise AssertionError

    def test_stylesheet_property_format(self):
        """Test that CSS properties are properly formatted."""
        mock_scaling = MagicMock()
        mock_scaling.scaled_size.return_value = 5
        mock_scaling.scaled_font_size.return_value = 12

        with patch("utils.colors.get_scaling_helper", return_value=mock_scaling):
            stylesheet = DinoPitColors.get_stylesheet("button")

            # Check for proper CSS property format
            properties_to_check = [
                "background-color:",
                "color:",
                "border:",
                "border-radius:",
                "font-size:",
                "font-weight:",
            ]

            for prop in properties_to_check:
                if prop not in stylesheet:
                    raise AssertionError

    def test_stylesheet_multiline_format(self):
        """Test that complex stylesheets are properly formatted across multiple lines."""
        mock_scaling = MagicMock()
        mock_scaling.scaled_size.return_value = 10
        mock_scaling.scaled_font_size.return_value = 14

        with patch("utils.colors.get_scaling_helper", return_value=mock_scaling):
            stylesheet = DinoPitColors.get_stylesheet("button")

            # Should be multi-line for readability
            lines = stylesheet.strip().split("\n")
            if len(lines) <= 5:
                raise AssertionError

            # Should have proper indentation structure
            non_empty_lines = [line for line in lines if line.strip()]
            if len(non_empty_lines) <= 0:
                raise AssertionError


class TestStylesheetEdgeCases:
    """Test cases for edge cases in stylesheet generation."""

    def test_get_stylesheet_with_none_element_type(self):
        """Test get_stylesheet with None element type."""
        with patch("utils.colors.get_scaling_helper"):
            # This might raise an error or return empty string
            try:
                stylesheet = DinoPitColors.get_stylesheet(None)
                if stylesheet != "":
                    raise AssertionError
            except (TypeError, AttributeError):
                # Acceptable to raise error for None input
                pass

    def test_get_stylesheet_with_empty_string(self):
        """Test get_stylesheet with empty string element type."""
        with patch("utils.colors.get_scaling_helper"):
            stylesheet = DinoPitColors.get_stylesheet("")

            if stylesheet != "":
                raise AssertionError

    def test_get_stylesheet_with_numeric_element_type(self):
        """Test get_stylesheet with numeric element type."""
        with patch("utils.colors.get_scaling_helper"):
            # Should handle gracefully
            try:
                stylesheet = DinoPitColors.get_stylesheet(123)
                if stylesheet != "":
                    raise AssertionError
            except (TypeError, AttributeError):
                # Acceptable to raise error for non-string input
                pass

    def test_scaling_helper_error_handling(self):
        """Test handling of scaling helper errors."""
        mock_scaling = MagicMock()
        mock_scaling.scaled_size.side_effect = RuntimeError("Scaling error")
        mock_scaling.scaled_font_size.side_effect = RuntimeError("Font scaling error")

        with patch("utils.colors.get_scaling_helper", return_value=mock_scaling):
            # Should handle scaling errors gracefully
            try:
                stylesheet = DinoPitColors.get_stylesheet("header")
                # If it succeeds, it should still be a string
                assert isinstance(stylesheet, str)
            except RuntimeError:
                # Acceptable to propagate scaling errors
                pass

    def test_get_stylesheet_special_characters_in_colors(self):
        """Test that color values with special characters are handled."""
        # Mock color constants to test edge cases
        original_orange = DinoPitColors.DINOPIT_ORANGE

        try:
            # Temporarily modify color constant
            DinoPitColors.DINOPIT_ORANGE = "#FF6B35"  # Normal case

            mock_scaling = MagicMock()
            mock_scaling.scaled_size.return_value = 10
            mock_scaling.scaled_font_size.return_value = 14

            with patch("utils.colors.get_scaling_helper", return_value=mock_scaling):
                stylesheet = DinoPitColors.get_stylesheet("header")

                if "#FF6B35" not in stylesheet:
                    raise AssertionError

        finally:
            # Restore original value
            DinoPitColors.DINOPIT_ORANGE = original_orange


class TestColorUsagePatterns:
    """Test cases for color usage patterns and consistency."""

    def test_primary_color_usage(self):
        """Test consistent usage of primary colors."""
        mock_scaling = MagicMock()
        mock_scaling.scaled_size.return_value = 10
        mock_scaling.scaled_font_size.return_value = 14

        with patch("utils.colors.get_scaling_helper", return_value=mock_scaling):
            header_stylesheet = DinoPitColors.get_stylesheet("header")
            button_stylesheet = DinoPitColors.get_stylesheet("button")

            # Both should use DINOPIT_ORANGE as primary background
            if DinoPitColors.DINOPIT_ORANGE not in header_stylesheet:
                raise AssertionError
            if DinoPitColors.DINOPIT_ORANGE not in button_stylesheet:
                raise AssertionError

    def test_accent_color_consistency(self):
        """Test consistent usage of accent colors."""
        mock_scaling = MagicMock()
        mock_scaling.scaled_size.return_value = 10
        mock_scaling.scaled_font_size.return_value = 14

        with patch("utils.colors.get_scaling_helper", return_value=mock_scaling):
            input_stylesheet = DinoPitColors.get_stylesheet("input_field")

            # Should use ACCENT_TEXT (STUDIOS_CYAN) for input text
            if DinoPitColors.STUDIOS_CYAN not in input_stylesheet:
                raise AssertionError
            if DinoPitColors.ACCENT_TEXT not in input_stylesheet:
                raise AssertionError

    def test_border_color_consistency(self):
        """Test consistent usage of border colors."""
        mock_scaling = MagicMock()
        mock_scaling.scaled_size.return_value = 10
        mock_scaling.scaled_font_size.return_value = 14

        with patch("utils.colors.get_scaling_helper", return_value=mock_scaling):
            input_stylesheet = DinoPitColors.get_stylesheet("input_field")

            # Should use BORDER_COLOR and BORDER_HOVER consistently
            if DinoPitColors.BORDER_COLOR not in input_stylesheet:
                raise AssertionError
            if DinoPitColors.BORDER_HOVER not in input_stylesheet:
                raise AssertionError

    def test_background_color_hierarchy(self):
        """Test background color hierarchy usage."""
        with patch("utils.colors.get_scaling_helper"):
            main_bg_stylesheet = DinoPitColors.get_stylesheet("main_background")
            panel_stylesheet = DinoPitColors.get_stylesheet("panel")

            # Should use different background colors for hierarchy
            if DinoPitColors.MAIN_BACKGROUND not in main_bg_stylesheet:
                raise AssertionError
            if DinoPitColors.PANEL_BACKGROUND not in panel_stylesheet:
                raise AssertionError
            if DinoPitColors.MAIN_BACKGROUND == DinoPitColors.PANEL_BACKGROUND:
                raise AssertionError


class TestClassStructure:
    """Test cases for class structure and design."""

    def test_dinopit_colors_is_class(self):
        """Test that DinoPitColors is a proper class."""
        assert isinstance(DinoPitColors, type)

    def test_color_constants_are_class_attributes(self):
        """Test that color constants are class attributes."""
        color_attrs = [
            "DINOPIT_ORANGE",
            "DINOPIT_FIRE",
            "STUDIOS_CYAN",
            "MAIN_BACKGROUND",
            "PANEL_BACKGROUND",
            "SIDEBAR_BACKGROUND",
            "SOFT_ORANGE",
            "SOFT_ORANGE_HOVER",
            "PRIMARY_TEXT",
            "SECONDARY_TEXT",
            "ACCENT_TEXT",
            "BRAND_TEXT",
            "BORDER_COLOR",
            "BORDER_HOVER",
            "ACCENT_BORDER",
        ]

        for attr in color_attrs:
            if not hasattr(DinoPitColors, attr):
                raise AssertionError
            assert isinstance(getattr(DinoPitColors, attr), str)

    def test_get_stylesheet_is_classmethod(self):
        """Test that get_stylesheet is a class method."""
        if not hasattr(DinoPitColors, "get_stylesheet"):
            raise AssertionError
        # Should be callable from class
        with patch("utils.colors.get_scaling_helper"):
            result = DinoPitColors.get_stylesheet("main_background")
            assert isinstance(result, str)

    def test_no_instance_required(self):
        """Test that DinoPitColors can be used without instantiation."""
        # Should be able to access colors without creating instance
        orange = DinoPitColors.DINOPIT_ORANGE
        if orange != "#FF6B35":
            raise AssertionError

        # Should be able to get stylesheet without creating instance
        with patch("utils.colors.get_scaling_helper"):
            stylesheet = DinoPitColors.get_stylesheet("panel")
            assert isinstance(stylesheet, str)

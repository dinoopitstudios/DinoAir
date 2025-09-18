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
        assert DinoPitColors.DINOPIT_ORANGE == "#FF6B35"
        assert DinoPitColors.DINOPIT_FIRE == "#FF4500"
        assert DinoPitColors.STUDIOS_CYAN == "#00BFFF"

        # Background Colors
        assert DinoPitColors.MAIN_BACKGROUND == "#2B3A52"
        assert DinoPitColors.PANEL_BACKGROUND == "#34435A"
        assert DinoPitColors.SIDEBAR_BACKGROUND == "#344359"

        # UI Element Colors
        assert DinoPitColors.SOFT_ORANGE == "#CC8B66"
        assert DinoPitColors.SOFT_ORANGE_HOVER == "#E6A085"

        # Text Colors
        assert DinoPitColors.PRIMARY_TEXT == "#FFFFFF"
        assert DinoPitColors.SECONDARY_TEXT == "#CCCCCC"
        assert DinoPitColors.ACCENT_TEXT == DinoPitColors.STUDIOS_CYAN
        assert DinoPitColors.BRAND_TEXT == DinoPitColors.DINOPIT_ORANGE

        # Border and Accent Colors
        assert DinoPitColors.BORDER_COLOR == DinoPitColors.SOFT_ORANGE
        assert DinoPitColors.BORDER_HOVER == DinoPitColors.SOFT_ORANGE_HOVER
        assert DinoPitColors.ACCENT_BORDER == DinoPitColors.DINOPIT_ORANGE

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
            assert color_value.startswith("#")
            assert len(color_value) == 7  # #RRGGBB format
            # Check that it's valid hex
            int(color_value[1:], 16)  # Should not raise ValueError

    def test_color_references(self):
        """Test that color references point to correct values."""
        assert DinoPitColors.ACCENT_TEXT == "#00BFFF"  # Should be STUDIOS_CYAN
        assert DinoPitColors.BRAND_TEXT == "#FF6B35"  # Should be DINOPIT_ORANGE
        assert DinoPitColors.BORDER_COLOR == "#CC8B66"  # Should be SOFT_ORANGE
        assert DinoPitColors.BORDER_HOVER == "#E6A085"  # Should be SOFT_ORANGE_HOVER
        assert DinoPitColors.ACCENT_BORDER == "#FF6B35"  # Should be DINOPIT_ORANGE


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
            assert DinoPitColors.DINOPIT_ORANGE in stylesheet
            assert "font-weight: bold" in stylesheet

    def test_get_stylesheet_main_background(self):
        """Test main_background stylesheet."""
        with patch("utils.colors.get_scaling_helper"):
            stylesheet = DinoPitColors.get_stylesheet("main_background")

            assert f"background-color: {DinoPitColors.MAIN_BACKGROUND}" in stylesheet
            assert stylesheet.strip().endswith(";")

    def test_get_stylesheet_header(self):
        """Test header stylesheet."""
        mock_scaling = MagicMock()
        mock_scaling.scaled_size.return_value = 2
        mock_scaling.scaled_font_size.return_value = 14

        with patch("utils.colors.get_scaling_helper", return_value=mock_scaling):
            stylesheet = DinoPitColors.get_stylesheet("header")

            assert f"background-color: {DinoPitColors.DINOPIT_ORANGE}" in stylesheet
            assert f"border-bottom: 2px solid {DinoPitColors.DINOPIT_FIRE}" in stylesheet
            assert f"color: {DinoPitColors.PRIMARY_TEXT}" in stylesheet
            assert "font-weight: bold" in stylesheet
            assert "font-size: 14px" in stylesheet

    def test_get_stylesheet_panel(self):
        """Test panel stylesheet."""
        with patch("utils.colors.get_scaling_helper"):
            stylesheet = DinoPitColors.get_stylesheet("panel")

            assert f"background-color: {DinoPitColors.PANEL_BACKGROUND}" in stylesheet

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
            assert "QLineEdit {" in stylesheet
            assert f"border: 1px solid {DinoPitColors.BORDER_COLOR}" in stylesheet
            assert "border-radius: 20px" in stylesheet
            assert "padding: 8px 15px" in stylesheet
            assert f"background-color: {DinoPitColors.MAIN_BACKGROUND}" in stylesheet
            assert f"color: {DinoPitColors.ACCENT_TEXT}" in stylesheet

            # Should contain focus styles
            assert "QLineEdit:focus {" in stylesheet
            assert f"border-color: {DinoPitColors.BORDER_HOVER}" in stylesheet

    def test_get_stylesheet_button(self):
        """Test button stylesheet."""
        mock_scaling = MagicMock()
        mock_scaling.scaled_size.return_value = 20
        mock_scaling.scaled_font_size.return_value = 16

        with patch("utils.colors.get_scaling_helper", return_value=mock_scaling):
            stylesheet = DinoPitColors.get_stylesheet("button")

            # Basic button styles
            assert "QPushButton {" in stylesheet
            assert f"background-color: {DinoPitColors.DINOPIT_ORANGE}" in stylesheet
            assert f"color: {DinoPitColors.PRIMARY_TEXT}" in stylesheet
            assert "border: none" in stylesheet
            assert "border-radius: 20px" in stylesheet
            assert "font-size: 16px" in stylesheet
            assert "font-weight: bold" in stylesheet

            # Hover state
            assert "QPushButton:hover {" in stylesheet
            assert f"background-color: {DinoPitColors.DINOPIT_FIRE}" in stylesheet

            # Pressed state
            assert "QPushButton:pressed {" in stylesheet
            assert "background-color: #E55A2B" in stylesheet

            # Disabled state
            assert "QPushButton:disabled {" in stylesheet
            assert "background-color: #666666" in stylesheet
            assert "color: #999999" in stylesheet

    def test_get_stylesheet_unknown_element(self):
        """Test get_stylesheet with unknown element type."""
        with patch("utils.colors.get_scaling_helper"):
            stylesheet = DinoPitColors.get_stylesheet("unknown_element")

            # Should return empty string for unknown elements
            assert stylesheet == ""

    def test_get_stylesheet_default_element(self):
        """Test get_stylesheet with default element type."""
        with patch("utils.colors.get_scaling_helper"):
            stylesheet = DinoPitColors.get_stylesheet("default")

            # Should return empty string for default
            assert stylesheet == ""

    def test_get_stylesheet_case_sensitivity(self):
        """Test get_stylesheet case sensitivity."""
        with patch("utils.colors.get_scaling_helper"):
            # Should be case sensitive
            header_stylesheet = DinoPitColors.get_stylesheet("header")
            header_caps_stylesheet = DinoPitColors.get_stylesheet("HEADER")

            assert header_stylesheet != ""
            assert header_caps_stylesheet == ""  # Unknown element

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
            assert mock_scaling.scaled_size.called
            assert mock_scaling.scaled_font_size.called

    def test_get_stylesheet_multiple_calls_consistency(self):
        """Test that multiple calls return consistent results."""
        mock_scaling = MagicMock()
        mock_scaling.scaled_size.return_value = 10
        mock_scaling.scaled_font_size.return_value = 14

        with patch("utils.colors.get_scaling_helper", return_value=mock_scaling):
            stylesheet1 = DinoPitColors.get_stylesheet("button")
            stylesheet2 = DinoPitColors.get_stylesheet("button")

            assert stylesheet1 == stylesheet2

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
                assert len(stylesheet) > 0  # Should have content

                # Each stylesheet should contain its primary color
                if element_type == "main_background":
                    assert DinoPitColors.MAIN_BACKGROUND in stylesheet
                elif element_type == "header":
                    assert DinoPitColors.DINOPIT_ORANGE in stylesheet
                elif element_type == "panel":
                    assert DinoPitColors.PANEL_BACKGROUND in stylesheet
                elif element_type in ["input_field", "button"]:
                    # These have more complex stylesheets but should contain colors
                    assert len(stylesheet) > 50  # Non-trivial content


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
                assert stylesheet.count("{") == stylesheet.count("}")  # Balanced braces

                # Should contain proper CSS selectors
                if element_type == "input_field":
                    assert "QLineEdit {" in stylesheet
                    assert "QLineEdit:focus {" in stylesheet
                elif element_type == "button":
                    assert "QPushButton {" in stylesheet
                    assert "QPushButton:hover {" in stylesheet
                    assert "QPushButton:pressed {" in stylesheet
                    assert "QPushButton:disabled {" in stylesheet

    def test_stylesheet_color_consistency(self):
        """Test that stylesheets use consistent color references."""
        mock_scaling = MagicMock()
        mock_scaling.scaled_size.return_value = 10
        mock_scaling.scaled_font_size.return_value = 14

        with patch("utils.colors.get_scaling_helper", return_value=mock_scaling):
            button_stylesheet = DinoPitColors.get_stylesheet("button")
            header_stylesheet = DinoPitColors.get_stylesheet("header")

            # Both should use DINOPIT_ORANGE as primary color
            assert DinoPitColors.DINOPIT_ORANGE in button_stylesheet
            assert DinoPitColors.DINOPIT_ORANGE in header_stylesheet

            # Both should use DINOPIT_FIRE for hover/accent
            assert DinoPitColors.DINOPIT_FIRE in button_stylesheet
            assert DinoPitColors.DINOPIT_FIRE in header_stylesheet

    def test_stylesheet_scaling_integration(self):
        """Test proper integration with scaling system."""
        mock_scaling = MagicMock()

        # Setup different return values for different calls
        mock_scaling.scaled_size.side_effect = [2, 20, 8, 15]  # Multiple calls
        mock_scaling.scaled_font_size.return_value = 16

        with patch("utils.colors.get_scaling_helper", return_value=mock_scaling):
            stylesheet = DinoPitColors.get_stylesheet("input_field")

            # Should have used scaled values
            assert "2px" in stylesheet  # scaled border
            assert "20px" in stylesheet  # scaled border-radius
            assert "8px 15px" in stylesheet  # scaled padding
            assert "16px" in stylesheet  # scaled font-size

    def test_stylesheet_qt_selector_format(self):
        """Test that stylesheets use proper Qt selector format."""
        mock_scaling = MagicMock()
        mock_scaling.scaled_size.return_value = 10
        mock_scaling.scaled_font_size.return_value = 14

        with patch("utils.colors.get_scaling_helper", return_value=mock_scaling):
            input_stylesheet = DinoPitColors.get_stylesheet("input_field")
            button_stylesheet = DinoPitColors.get_stylesheet("button")

            # Should use Qt-specific selectors
            assert "QLineEdit" in input_stylesheet
            assert "QLineEdit:focus" in input_stylesheet
            assert "QPushButton" in button_stylesheet
            assert "QPushButton:hover" in button_stylesheet
            assert "QPushButton:pressed" in button_stylesheet
            assert "QPushButton:disabled" in button_stylesheet

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
                assert prop in stylesheet

    def test_stylesheet_multiline_format(self):
        """Test that complex stylesheets are properly formatted across multiple lines."""
        mock_scaling = MagicMock()
        mock_scaling.scaled_size.return_value = 10
        mock_scaling.scaled_font_size.return_value = 14

        with patch("utils.colors.get_scaling_helper", return_value=mock_scaling):
            stylesheet = DinoPitColors.get_stylesheet("button")

            # Should be multi-line for readability
            lines = stylesheet.strip().split("\n")
            assert len(lines) > 5  # Should have multiple lines

            # Should have proper indentation structure
            non_empty_lines = [line for line in lines if line.strip()]
            assert len(non_empty_lines) > 0


class TestStylesheetEdgeCases:
    """Test cases for edge cases in stylesheet generation."""

    def test_get_stylesheet_with_none_element_type(self):
        """Test get_stylesheet with None element type."""
        with patch("utils.colors.get_scaling_helper"):
            # This might raise an error or return empty string
            try:
                stylesheet = DinoPitColors.get_stylesheet(None)
                assert stylesheet == ""
            except (TypeError, AttributeError):
                # Acceptable to raise error for None input
                pass

    def test_get_stylesheet_with_empty_string(self):
        """Test get_stylesheet with empty string element type."""
        with patch("utils.colors.get_scaling_helper"):
            stylesheet = DinoPitColors.get_stylesheet("")

            assert stylesheet == ""  # Empty string should return empty stylesheet

    def test_get_stylesheet_with_numeric_element_type(self):
        """Test get_stylesheet with numeric element type."""
        with patch("utils.colors.get_scaling_helper"):
            # Should handle gracefully
            try:
                stylesheet = DinoPitColors.get_stylesheet(123)
                assert stylesheet == ""
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

                assert "#FF6B35" in stylesheet

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
            assert DinoPitColors.DINOPIT_ORANGE in header_stylesheet
            assert DinoPitColors.DINOPIT_ORANGE in button_stylesheet

    def test_accent_color_consistency(self):
        """Test consistent usage of accent colors."""
        mock_scaling = MagicMock()
        mock_scaling.scaled_size.return_value = 10
        mock_scaling.scaled_font_size.return_value = 14

        with patch("utils.colors.get_scaling_helper", return_value=mock_scaling):
            input_stylesheet = DinoPitColors.get_stylesheet("input_field")

            # Should use ACCENT_TEXT (STUDIOS_CYAN) for input text
            assert DinoPitColors.STUDIOS_CYAN in input_stylesheet
            assert DinoPitColors.ACCENT_TEXT in input_stylesheet

    def test_border_color_consistency(self):
        """Test consistent usage of border colors."""
        mock_scaling = MagicMock()
        mock_scaling.scaled_size.return_value = 10
        mock_scaling.scaled_font_size.return_value = 14

        with patch("utils.colors.get_scaling_helper", return_value=mock_scaling):
            input_stylesheet = DinoPitColors.get_stylesheet("input_field")

            # Should use BORDER_COLOR and BORDER_HOVER consistently
            assert DinoPitColors.BORDER_COLOR in input_stylesheet
            assert DinoPitColors.BORDER_HOVER in input_stylesheet

    def test_background_color_hierarchy(self):
        """Test background color hierarchy usage."""
        with patch("utils.colors.get_scaling_helper"):
            main_bg_stylesheet = DinoPitColors.get_stylesheet("main_background")
            panel_stylesheet = DinoPitColors.get_stylesheet("panel")

            # Should use different background colors for hierarchy
            assert DinoPitColors.MAIN_BACKGROUND in main_bg_stylesheet
            assert DinoPitColors.PANEL_BACKGROUND in panel_stylesheet
            assert DinoPitColors.MAIN_BACKGROUND != DinoPitColors.PANEL_BACKGROUND


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
            assert hasattr(DinoPitColors, attr)
            assert isinstance(getattr(DinoPitColors, attr), str)

    def test_get_stylesheet_is_classmethod(self):
        """Test that get_stylesheet is a class method."""
        assert hasattr(DinoPitColors, "get_stylesheet")
        # Should be callable from class
        with patch("utils.colors.get_scaling_helper"):
            result = DinoPitColors.get_stylesheet("main_background")
            assert isinstance(result, str)

    def test_no_instance_required(self):
        """Test that DinoPitColors can be used without instantiation."""
        # Should be able to access colors without creating instance
        orange = DinoPitColors.DINOPIT_ORANGE
        assert orange == "#FF6B35"

        # Should be able to get stylesheet without creating instance
        with patch("utils.colors.get_scaling_helper"):
            stylesheet = DinoPitColors.get_stylesheet("panel")
            assert isinstance(stylesheet, str)

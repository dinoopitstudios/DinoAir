import importlib
import sys
import warnings


def test_import_llm_interface_emits_deprecation_warning():
    # Ensure fresh import to trigger import-time warnings
    mod_name = "pseudocode_translator.llm_interface"
    if mod_name in sys.modules:
        del sys.modules[mod_name]

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        module = importlib.import_module(mod_name)

        assert module is not None

        # Verify a DeprecationWarning mentioning deprecation was emitted
        messages = [
            str(w.message).lower() for w in caught if isinstance(w.message, DeprecationWarning)
        ]
        if not any("deprecated" in msg for msg in messages):
            raise AssertionError(
                f"No deprecation warning found. Captured: {messages}"
            )

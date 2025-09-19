"""
Unit tests for state_machine.py module.
Tests state machine functionality, transitions, validators, and callbacks.
"""

import threading
import time
from datetime import datetime
from unittest.mock import MagicMock, patch

from ..state_machine import (
    ApplicationState,
    DefaultStateValidator,
    StateInfo,
    StateMachine,
    StateTransition,
    StateValidator,
    TransitionResult,
    get_current_state,
    get_state_machine,
    transition_to_state,
)


class TestApplicationState:
    """Test cases for ApplicationState enum."""

    def test_application_state_values(self):
        """Test ApplicationState enum values."""
        if ApplicationState.INITIALIZING.value != "initializing":
            raise AssertionError
        if ApplicationState.STARTING.value != "starting":
            raise AssertionError
        if ApplicationState.RUNNING.value != "running":
            raise AssertionError
        if ApplicationState.PAUSING.value != "pausing":
            raise AssertionError
        if ApplicationState.PAUSED.value != "paused":
            raise AssertionError
        if ApplicationState.RESUMING.value != "resuming":
            raise AssertionError
        if ApplicationState.SHUTTING_DOWN.value != "shutting_down":
            raise AssertionError
        if ApplicationState.SHUTDOWN.value != "shutdown":
            raise AssertionError
        if ApplicationState.ERROR.value != "error":
            raise AssertionError
        if ApplicationState.MAINTENANCE.value != "maintenance":
            raise AssertionError

    def test_application_state_membership(self):
        """Test ApplicationState enum membership."""
        all_states = {
            ApplicationState.INITIALIZING,
            ApplicationState.STARTING,
            ApplicationState.RUNNING,
            ApplicationState.PAUSING,
            ApplicationState.PAUSED,
            ApplicationState.RESUMING,
            ApplicationState.SHUTTING_DOWN,
            ApplicationState.SHUTDOWN,
            ApplicationState.ERROR,
            ApplicationState.MAINTENANCE,
        }
        assert len(all_states) == 10


class TestTransitionResult:
    """Test cases for TransitionResult enum."""

    def test_transition_result_values(self):
        """Test TransitionResult enum values."""
        if TransitionResult.SUCCESS.value != "success":
            raise AssertionError
        if TransitionResult.FAILED.value != "failed":
            raise AssertionError
        if TransitionResult.BLOCKED.value != "blocked":
            raise AssertionError
        if TransitionResult.INVALID.value != "invalid":
            raise AssertionError


class TestStateTransition:
    """Test cases for StateTransition dataclass."""

    def test_state_transition_creation(self):
        """Test StateTransition creation with all fields."""
        timestamp = datetime.now()
        transition = StateTransition(
            from_state=ApplicationState.STARTING,
            to_state=ApplicationState.RUNNING,
            timestamp=timestamp,
            duration_ms=150,
            result=TransitionResult.SUCCESS,
            error_message=None,
            metadata={"user": "test_user"},
        )

        if transition.from_state != ApplicationState.STARTING:
            raise AssertionError
        if transition.to_state != ApplicationState.RUNNING:
            raise AssertionError
        if transition.timestamp != timestamp:
            raise AssertionError
        if transition.duration_ms != 150:
            raise AssertionError
        if transition.result != TransitionResult.SUCCESS:
            raise AssertionError
        assert transition.error_message is None
        if transition.metadata != {"user": "test_user"}:
            raise AssertionError

    def test_state_transition_with_error(self):
        """Test StateTransition creation with error."""
        transition = StateTransition(
            from_state=ApplicationState.RUNNING,
            to_state=ApplicationState.ERROR,
            timestamp=datetime.now(),
            duration_ms=50,
            result=TransitionResult.FAILED,
            error_message="Test error occurred",
        )

        if transition.result != TransitionResult.FAILED:
            raise AssertionError
        if transition.error_message != "Test error occurred":
            raise AssertionError


class TestStateInfo:
    """Test cases for StateInfo dataclass."""

    def test_state_info_creation(self):
        """Test StateInfo creation."""
        entry_time = datetime.now()
        info = StateInfo(
            state=ApplicationState.RUNNING,
            entry_time=entry_time,
            duration_ms=5000,
            entry_count=3,
            metadata={"performance": "good"},
        )

        if info.state != ApplicationState.RUNNING:
            raise AssertionError
        if info.entry_time != entry_time:
            raise AssertionError
        if info.duration_ms != 5000:
            raise AssertionError
        if info.entry_count != 3:
            raise AssertionError
        if info.metadata != {"performance": "good"}:
            raise AssertionError

    def test_state_info_defaults(self):
        """Test StateInfo with default values."""
        info = StateInfo(state=ApplicationState.INITIALIZING,
                         entry_time=datetime.now())

        if info.duration_ms != 0:
            raise AssertionError
        if info.entry_count != 0:
            raise AssertionError
        if info.metadata != {}:
            raise AssertionError


class TestDefaultStateValidator:
    """Test cases for DefaultStateValidator."""

    def test_default_validator_initialization(self):
        """Test DefaultStateValidator initialization."""
        validator = DefaultStateValidator()
        if not hasattr(validator, "_valid_transitions"):
            raise AssertionError

    def test_valid_transitions(self):
        """Test valid state transitions."""
        validator = DefaultStateValidator()

        # Test some valid transitions
        valid_transitions = [
            (ApplicationState.INITIALIZING, ApplicationState.STARTING),
            (ApplicationState.STARTING, ApplicationState.RUNNING),
            (ApplicationState.RUNNING, ApplicationState.PAUSING),
            (ApplicationState.PAUSED, ApplicationState.RESUMING),
            (ApplicationState.RESUMING, ApplicationState.RUNNING),
            (ApplicationState.RUNNING, ApplicationState.SHUTTING_DOWN),
            (ApplicationState.SHUTTING_DOWN, ApplicationState.SHUTDOWN),
        ]

        for from_state, to_state in valid_transitions:
            can_transition, error_msg = validator.can_transition(
                from_state, to_state, {})
            if can_transition is not True:
                raise AssertionError(
                    f"Should allow {from_state.value} -> {to_state.value}")
            if error_msg != "":
                raise AssertionError

    def test_invalid_transitions(self):
        """Test invalid state transitions."""
        validator = DefaultStateValidator()

        # Test some invalid transitions
        invalid_transitions = [
            (ApplicationState.SHUTDOWN, ApplicationState.RUNNING),  # Terminal state
            (ApplicationState.INITIALIZING,
             ApplicationState.RUNNING),  # Skip starting
            (ApplicationState.PAUSED, ApplicationState.STARTING),  # Wrong direction
        ]

        for from_state, to_state in invalid_transitions:
            can_transition, error_msg = validator.can_transition(
                from_state, to_state, {})
            if can_transition is not False:
                raise AssertionError(
                    f"Should block {from_state.value} -> {to_state.value}")
            if error_msg == "":
                raise AssertionError

    def test_error_state_transitions(self):
        """Test transitions from ERROR state."""
        validator = DefaultStateValidator()

        # ERROR state should allow limited transitions
        valid_from_error = [
            ApplicationState.SHUTTING_DOWN,
            ApplicationState.SHUTDOWN,
            ApplicationState.MAINTENANCE,
        ]

        for to_state in valid_from_error:
            can_transition, error_msg = validator.can_transition(
                ApplicationState.ERROR, to_state, {}
            )
            if can_transition is not True:
                raise AssertionError

        # Should block transition back to RUNNING directly
        can_transition, error_msg = validator.can_transition(
            ApplicationState.ERROR, ApplicationState.RUNNING, {}
        )
        if can_transition is not False:
            raise AssertionError

    def test_maintenance_state_transitions(self):
        """Test transitions from MAINTENANCE state."""
        validator = DefaultStateValidator()

        valid_from_maintenance = [
            ApplicationState.RUNNING,
            ApplicationState.SHUTTING_DOWN,
            ApplicationState.ERROR,
        ]

        for to_state in valid_from_maintenance:
            can_transition, error_msg = validator.can_transition(
                ApplicationState.MAINTENANCE, to_state, {}
            )
            if can_transition is not True:
                raise AssertionError


class TestStateMachine:
    """Test cases for StateMachine class."""

    def test_state_machine_initialization(self):
        """Test StateMachine initialization."""
        state_machine = StateMachine()

        if state_machine.get_current_state() != ApplicationState.INITIALIZING:
            raise AssertionError
        if state_machine.get_previous_state() is not None:
            raise AssertionError

    def test_state_machine_custom_initial_state(self):
        """Test StateMachine with custom initial state."""
        state_machine = StateMachine(initial_state=ApplicationState.RUNNING)

        if state_machine.get_current_state() != ApplicationState.RUNNING:
            raise AssertionError

    def test_state_machine_custom_validator(self):
        """Test StateMachine with custom validator."""
        mock_validator = MagicMock()
        mock_validator.can_transition.return_value = (True, "")

        state_machine = StateMachine(validator=mock_validator)
        if state_machine.validator != mock_validator:
            raise AssertionError

    def test_successful_transition(self):
        """Test successful state transition."""
        state_machine = StateMachine()

        result = state_machine.transition_to(ApplicationState.STARTING)

        if result != TransitionResult.SUCCESS:
            raise AssertionError
        if state_machine.get_current_state() != ApplicationState.STARTING:
            raise AssertionError
        if state_machine.get_previous_state() != ApplicationState.INITIALIZING:
            raise AssertionError

    def test_blocked_transition(self):
        """Test blocked state transition."""
        state_machine = StateMachine()

        # Try invalid transition (INITIALIZING -> RUNNING, should go through STARTING)
        result = state_machine.transition_to(ApplicationState.RUNNING)

        if result != TransitionResult.BLOCKED:
            raise AssertionError
        if state_machine.get_current_state() != ApplicationState.INITIALIZING:
            raise AssertionError

    def test_transition_to_same_state(self):
        """Test transition to the same state."""
        state_machine = StateMachine()

        result = state_machine.transition_to(ApplicationState.INITIALIZING)

        if result != TransitionResult.SUCCESS:
            raise AssertionError
        if state_machine.get_current_state() != ApplicationState.INITIALIZING:
            raise AssertionError

    def test_forced_transition(self):
        """Test forced state transition."""
        state_machine = StateMachine()

        # Force invalid transition
        result = state_machine.transition_to(
            ApplicationState.RUNNING, force=True)

        if result != TransitionResult.SUCCESS:
            raise AssertionError
        if state_machine.get_current_state() != ApplicationState.RUNNING:
            raise AssertionError

    def test_transition_with_context(self):
        """Test state transition with context."""
        state_machine = StateMachine()

        context = {"reason": "test transition", "user": "test_user"}
        result = state_machine.transition_to(
            ApplicationState.STARTING, context=context)

        if result != TransitionResult.SUCCESS:
            raise AssertionError

        # Check that context was recorded in history
        history = state_machine.get_state_history(limit=1)
        assert len(history) == 1
        if history[0].metadata != context:
            raise AssertionError

    def test_transition_callbacks(self):
        """Test state transition callbacks."""
        state_machine = StateMachine()

        enter_callback = MagicMock()
        exit_callback = MagicMock()
        transition_callback = MagicMock()

        # Register callbacks
        state_machine.on_enter(ApplicationState.STARTING, enter_callback)
        state_machine.on_exit(ApplicationState.INITIALIZING, exit_callback)
        state_machine.on_transition(transition_callback)

        # Perform transition
        state_machine.transition_to(ApplicationState.STARTING)

        # Verify callbacks were called
        enter_callback.assert_called_once()
        exit_callback.assert_called_once()
        transition_callback.assert_called_once()

    def test_callback_error_handling(self):
        """Test error handling in callbacks."""
        state_machine = StateMachine()

        def failing_callback(*args, **kwargs):
            raise RuntimeError("Callback error")

        state_machine.on_enter(ApplicationState.STARTING, failing_callback)

        # Transition should still succeed despite callback error
        with patch("utils.state_machine.logger") as mock_logger:
            result = state_machine.transition_to(ApplicationState.STARTING)

            if result != TransitionResult.SUCCESS:
                raise AssertionError
            mock_logger.error.assert_called()

    def test_get_state_history(self):
        """Test getting state history."""
        state_machine = StateMachine()

        # Perform some transitions
        state_machine.transition_to(ApplicationState.STARTING)
        state_machine.transition_to(ApplicationState.RUNNING)

        history = state_machine.get_state_history()

        assert len(history) == 2
        if history[0].from_state != ApplicationState.INITIALIZING:
            raise AssertionError
        if history[0].to_state != ApplicationState.STARTING:
            raise AssertionError
        if history[1].from_state != ApplicationState.STARTING:
            raise AssertionError
        if history[1].to_state != ApplicationState.RUNNING:
            raise AssertionError

    def test_get_state_history_with_limit(self):
        """Test getting state history with limit."""
        state_machine = StateMachine()

        # Perform multiple transitions
        state_machine.transition_to(ApplicationState.STARTING)
        state_machine.transition_to(ApplicationState.RUNNING)
        state_machine.transition_to(ApplicationState.PAUSING)

        history = state_machine.get_state_history(limit=2)

        assert len(history) == 2
        # Should get the most recent transitions
        if history[-1].to_state != ApplicationState.PAUSING:
            raise AssertionError

    def test_get_state_info(self):
        """Test getting state information."""
        state_machine = StateMachine()

        # Get info for initial state
        info = state_machine.get_state_info(ApplicationState.INITIALIZING)

        assert info is not None
        if info.state != ApplicationState.INITIALIZING:
            raise AssertionError
        if info.entry_count != 1:
            raise AssertionError

        # Transition and check info updates
        state_machine.transition_to(ApplicationState.STARTING)
        starting_info = state_machine.get_state_info(ApplicationState.STARTING)

        assert starting_info is not None
        if starting_info.entry_count != 1:
            raise AssertionError

    def test_get_all_state_info(self):
        """Test getting all state information."""
        state_machine = StateMachine()

        # Perform some transitions
        state_machine.transition_to(ApplicationState.STARTING)
        state_machine.transition_to(ApplicationState.RUNNING)

        all_info = state_machine.get_all_state_info()

        if ApplicationState.INITIALIZING not in all_info:
            raise AssertionError
        if ApplicationState.STARTING not in all_info:
            raise AssertionError
        if ApplicationState.RUNNING not in all_info:
            raise AssertionError

    def test_get_current_state_duration(self):
        """Test getting current state duration."""
        state_machine = StateMachine()

        # Sleep briefly to ensure measurable duration
        time.sleep(0.01)

        duration = state_machine.get_current_state_duration()

        if duration <= 0:
            raise AssertionError
        assert isinstance(duration, int)

    def test_is_in_state(self):
        """Test checking if in specific state(s)."""
        state_machine = StateMachine()

        if state_machine.is_in_state(ApplicationState.INITIALIZING) is not True:
            raise AssertionError
        if state_machine.is_in_state(ApplicationState.RUNNING) is not False:
            raise AssertionError
        if (
            state_machine.is_in_state(
                ApplicationState.INITIALIZING, ApplicationState.STARTING)
            is not True
        ):
            raise AssertionError

        # Transition and test again
        state_machine.transition_to(ApplicationState.STARTING)
        if state_machine.is_in_state(ApplicationState.STARTING) is not True:
            raise AssertionError
        if state_machine.is_in_state(ApplicationState.INITIALIZING) is not False:
            raise AssertionError

    def test_wait_for_state(self):
        """Test waiting for a specific state."""
        state_machine = StateMachine()

        def delayed_transition():
            time.sleep(0.1)
            state_machine.transition_to(ApplicationState.STARTING)

        # Start background transition
        thread = threading.Thread(target=delayed_transition)
        thread.start()

        # Wait for state
        success = state_machine.wait_for_state(
            ApplicationState.STARTING, timeout=1.0)

        thread.join()
        if success is not True:
            raise AssertionError
        if state_machine.get_current_state() != ApplicationState.STARTING:
            raise AssertionError

    def test_wait_for_state_timeout(self):
        """Test waiting for state with timeout."""
        state_machine = StateMachine()

        # Wait for state that will never occur
        success = state_machine.wait_for_state(
            ApplicationState.SHUTDOWN, timeout=0.1)

        if success is not False:
            raise AssertionError
        if state_machine.get_current_state() != ApplicationState.INITIALIZING:
            raise AssertionError

    def test_get_status_report(self):
        """Test getting comprehensive status report."""
        state_machine = StateMachine()

        # Perform some transitions
        state_machine.transition_to(ApplicationState.STARTING)
        state_machine.transition_to(ApplicationState.RUNNING)

        report = state_machine.get_status_report()

        if report["current_state"] != "running":
            raise AssertionError
        if report["previous_state"] != "starting":
            raise AssertionError
        if "current_state_duration_ms" not in report:
            raise AssertionError
        if "total_transitions" not in report:
            raise AssertionError
        if "successful_transitions" not in report:
            raise AssertionError
        if "success_rate" not in report:
            raise AssertionError
        if "state_statistics" not in report:
            raise AssertionError
        if "recent_transitions" not in report:
            raise AssertionError

        # Check that all transitions were successful
        if report["total_transitions"] != 2:
            raise AssertionError
        if report["successful_transitions"] != 2:
            raise AssertionError
        if report["success_rate"] != 100.0:
            raise AssertionError

    def test_reset_state_machine(self):
        """Test resetting the state machine."""
        state_machine = StateMachine()

        # Perform some transitions
        state_machine.transition_to(ApplicationState.STARTING)
        state_machine.transition_to(ApplicationState.RUNNING)

        # Reset to default state
        state_machine.reset()

        if state_machine.get_current_state() != ApplicationState.INITIALIZING:
            raise AssertionError
        if state_machine.get_previous_state() is not None:
            raise AssertionError

        # History should be cleared (except reset transition)
        history = state_machine.get_state_history()
        assert len(history) == 1  # Only the reset transition
        if history[0].error_message != "State machine reset":
            raise AssertionError

    def test_reset_to_custom_state(self):
        """Test resetting to custom initial state."""
        state_machine = StateMachine()

        state_machine.reset(initial_state=ApplicationState.MAINTENANCE)

        if state_machine.get_current_state() != ApplicationState.MAINTENANCE:
            raise AssertionError

    def test_transition_error_handling(self):
        """Test error handling during transitions."""

        def failing_callback(*args, **kwargs):
            raise RuntimeError("Transition failed")

        state_machine = StateMachine()
        state_machine.on_enter(ApplicationState.STARTING, failing_callback)

        with patch("utils.state_machine.logger") as mock_logger:
            result = state_machine.transition_to(ApplicationState.STARTING)

            # Transition should fail due to callback error
            if result != TransitionResult.FAILED:
                raise AssertionError
            mock_logger.error.assert_called()

    def test_thread_safety(self):
        """Test thread safety of state machine."""
        state_machine = StateMachine()
        results = {}

        def worker(thread_id, target_state):
            result = state_machine.transition_to(target_state)
            results[thread_id] = result

        # Start multiple threads trying to transition
        threads = []
        target_states = [ApplicationState.STARTING, ApplicationState.ERROR]

        for i, target in enumerate(target_states):
            thread = threading.Thread(target=worker, args=(i, target))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # At least one transition should succeed
        successful_results = [
            r for r in results.values() if r == TransitionResult.SUCCESS]
        if len(successful_results) < 1:
            raise AssertionError

    def test_state_history_size_limit(self):
        """Test that state history is limited in size."""
        state_machine = StateMachine()

        # Perform many transitions to test history limiting
        for i in range(1005):  # More than the 1000 limit
            if i % 2 == 0:
                state_machine.transition_to(
                    ApplicationState.STARTING, force=True)
            else:
                state_machine.transition_to(
                    ApplicationState.INITIALIZING, force=True)

        history = state_machine.get_state_history()

        # History should be limited to 500 (after trimming)
        if len(history) > 500:
            raise AssertionError

    def test_multiple_entry_to_same_state(self):
        """Test multiple entries to the same state."""
        state_machine = StateMachine()

        # Transition to STARTING multiple times
        state_machine.transition_to(ApplicationState.STARTING)
        state_machine.transition_to(ApplicationState.INITIALIZING, force=True)
        state_machine.transition_to(ApplicationState.STARTING)

        info = state_machine.get_state_info(ApplicationState.STARTING)
        if info.entry_count != 2:
            raise AssertionError


class TestCustomStateValidator:
    """Test cases for custom state validators."""

    def test_custom_validator_implementation(self):
        """Test implementing a custom state validator."""

        class StrictValidator(StateValidator):
            def can_transition(self, from_state, to_state, context):
                # Only allow very specific transitions
                if (
                    from_state == ApplicationState.INITIALIZING
                    and to_state == ApplicationState.STARTING
                ):
                    return True, ""
                return False, "Strict validator blocks this transition"

        validator = StrictValidator()
        state_machine = StateMachine(validator=validator)

        # Should allow INITIALIZING -> STARTING
        result = state_machine.transition_to(ApplicationState.STARTING)
        if result != TransitionResult.SUCCESS:
            raise AssertionError

        # Should block STARTING -> RUNNING
        result = state_machine.transition_to(ApplicationState.RUNNING)
        if result != TransitionResult.BLOCKED:
            raise AssertionError

    def test_context_based_validation(self):
        """Test validator that uses context for decisions."""

        class ContextValidator(StateValidator):
            def can_transition(self, from_state, to_state, context):
                if to_state == ApplicationState.MAINTENANCE:
                    # Only allow maintenance if authorized
                    if context.get("authorized_maintenance"):
                        return True, ""
                    return False, "Maintenance requires authorization"
                return True, ""  # Allow other transitions

        validator = ContextValidator()
        state_machine = StateMachine(
            initial_state=ApplicationState.RUNNING, validator=validator)

        # Should block maintenance without authorization
        result = state_machine.transition_to(ApplicationState.MAINTENANCE)
        if result != TransitionResult.BLOCKED:
            raise AssertionError

        # Should allow maintenance with authorization
        result = state_machine.transition_to(
            ApplicationState.MAINTENANCE, context={
                "authorized_maintenance": True}
        )
        if result != TransitionResult.SUCCESS:
            raise AssertionError


class TestGlobalStateMachine:
    """Test cases for global state machine functions."""

    def test_get_state_machine_singleton(self):
        """Test that global state machine is singleton."""
        sm1 = get_state_machine()
        sm2 = get_state_machine()

        if sm1 is not sm2:
            raise AssertionError
        assert isinstance(sm1, StateMachine)

    def test_get_current_state_function(self):
        """Test global get_current_state function."""
        # Reset global state machine
        with patch("utils.state_machine._state_machine", None):
            current_state = get_current_state()
            if current_state != ApplicationState.INITIALIZING:
                raise AssertionError

    def test_transition_to_state_function(self):
        """Test global transition_to_state function."""
        result = transition_to_state(ApplicationState.STARTING)
        if result != TransitionResult.SUCCESS:
            raise AssertionError

        current_state = get_current_state()
        if current_state != ApplicationState.STARTING:
            raise AssertionError

    def test_global_state_machine_thread_safety(self):
        """Test thread safety of global state machine access."""
        results = {}

        def worker(thread_id):
            sm = get_state_machine()
            results[thread_id] = id(sm)

        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All threads should get the same instance
        unique_ids = set(results.values())
        assert len(unique_ids) == 1


class TestStateMachineEdgeCases:
    """Test cases for edge cases and error conditions."""

    def test_rapid_transitions(self):
        """Test rapid state transitions."""
        state_machine = StateMachine()

        # Perform rapid transitions
        start_time = time.time()
        transition_count = 0

        for _ in range(100):
            if state_machine.get_current_state() == ApplicationState.INITIALIZING:
                result = state_machine.transition_to(ApplicationState.STARTING)
            else:
                result = state_machine.transition_to(
                    ApplicationState.INITIALIZING, force=True)

            if result == TransitionResult.SUCCESS:
                transition_count += 1

        end_time = time.time()
        duration = end_time - start_time

        # Should handle rapid transitions efficiently
        if duration >= 1.0:
            raise AssertionError
        if transition_count <= 0:
            raise AssertionError

    def test_concurrent_transitions(self):
        """Test concurrent state transitions."""
        state_machine = StateMachine()
        results = []
        lock = threading.Lock()

        def concurrent_worker(target_state):
            result = state_machine.transition_to(target_state, force=True)
            with lock:
                results.append((target_state, result))

        # Start concurrent transitions
        threads = []
        states = [ApplicationState.STARTING,
                  ApplicationState.ERROR, ApplicationState.MAINTENANCE]

        for state in states:
            thread = threading.Thread(target=concurrent_worker, args=(state,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Should have attempted all transitions
        assert len(results) == 3

        # At least one should succeed (due to forced transitions)
        successful = [r for _, r in results if r == TransitionResult.SUCCESS]
        if len(successful) < 1:
            raise AssertionError

    def test_state_duration_accuracy(self):
        """Test accuracy of state duration measurements."""
        state_machine = StateMachine()

        # Transition and wait
        state_machine.transition_to(ApplicationState.STARTING)
        time.sleep(0.1)

        duration = state_machine.get_current_state_duration()

        # Duration should be approximately 100ms (allow some variance)
        if not 80 <= duration <= 200:
            raise AssertionError

    def test_large_metadata_handling(self):
        """Test handling of large metadata in transitions."""
        state_machine = StateMachine()

        # Create large metadata
        large_metadata = {f"key_{i}": f"value_{i}" * 100 for i in range(100)}

        result = state_machine.transition_to(
            ApplicationState.STARTING, context=large_metadata)

        if result != TransitionResult.SUCCESS:
            raise AssertionError

        # Verify metadata was stored
        history = state_machine.get_state_history(limit=1)
        assert len(history[0].metadata) == 100

    def test_state_machine_under_stress(self):
        """Test state machine performance under stress."""
        state_machine = StateMachine()

        start_time = time.time()

        # Perform many operations
        for i in range(1000):
            if i % 100 == 0:
                state_machine.get_status_report()
            if i % 50 == 0:
                state_machine.get_state_history(limit=10)

            # Alternate between states
            if i % 2 == 0:
                state_machine.transition_to(
                    ApplicationState.STARTING, force=True)
            else:
                state_machine.transition_to(
                    ApplicationState.INITIALIZING, force=True)

        end_time = time.time()
        duration = end_time - start_time

        # Should complete in reasonable time
        if duration >= 5.0:
            raise AssertionError

        # State machine should still be functional
        current_state = state_machine.get_current_state()
        if current_state not in [ApplicationState.INITIALIZING, ApplicationState.STARTING]:
            raise AssertionError


class TestStateMachineIntegration:
    """Integration test cases for state machine."""

    def test_full_application_lifecycle(self):
        """Test complete application lifecycle transitions."""
        state_machine = StateMachine()

        # Simulate full application lifecycle
        lifecycle_states = [
            ApplicationState.STARTING,
            ApplicationState.RUNNING,
            ApplicationState.PAUSING,
            ApplicationState.PAUSED,
            ApplicationState.RESUMING,
            ApplicationState.RUNNING,
            ApplicationState.SHUTTING_DOWN,
            ApplicationState.SHUTDOWN,
        ]

        for target_state in lifecycle_states:
            result = state_machine.transition_to(target_state)
            if result != TransitionResult.SUCCESS:
                raise AssertionError(
                    f"Failed to transition to {target_state.value}")

        if state_machine.get_current_state() != ApplicationState.SHUTDOWN:
            raise AssertionError

        # Check that all states were recorded
        all_info = state_machine.get_all_state_info()
        for state in lifecycle_states:
            if state not in all_info:
                raise AssertionError

    def test_error_recovery_workflow(self):
        """Test error recovery workflow."""
        state_machine = StateMachine()

        # Normal startup
        state_machine.transition_to(ApplicationState.STARTING)
        state_machine.transition_to(ApplicationState.RUNNING)

        # Simulate error
        state_machine.transition_to(ApplicationState.ERROR)

        # Recovery through maintenance
        state_machine.transition_to(ApplicationState.MAINTENANCE)
        state_machine.transition_to(ApplicationState.RUNNING)

        if state_machine.get_current_state() != ApplicationState.RUNNING:
            raise AssertionError

        # Check error was recorded in history
        history = state_machine.get_state_history()
        error_transitions = [
            h for h in history if h.to_state == ApplicationState.ERROR]
        assert len(error_transitions) == 1

    def test_monitoring_integration(self):
        """Test integration with monitoring/logging systems."""
        state_machine = StateMachine()

        # Mock monitoring callbacks
        monitoring_data = []

        def monitor_callback(from_state, to_state, context):
            monitoring_data.append(
                {
                    "from": from_state.value,
                    "to": to_state.value,
                    "timestamp": time.time(),
                    "context": context,
                }
            )

        state_machine.on_transition(monitor_callback)

        # Perform transitions
        state_machine.transition_to(ApplicationState.STARTING)
        state_machine.transition_to(
            ApplicationState.RUNNING, context={"load": "high"})

        # Verify monitoring data was collected
        assert len(monitoring_data) == 2
        if monitoring_data[0]["from"] != "initializing":
            raise AssertionError
        if monitoring_data[0]["to"] != "starting":
            raise AssertionError
        if monitoring_data[1]["context"]["load"] != "high":
            raise AssertionError

    def test_persistence_simulation(self):
        """Test simulation of state persistence."""
        # This simulates how state could be persisted and restored
        state_machine = StateMachine()

        # Perform some transitions
        state_machine.transition_to(ApplicationState.STARTING)
        state_machine.transition_to(ApplicationState.RUNNING)

        # Get state for "persistence"
        current_state = state_machine.get_current_state()
        state_machine.get_status_report()

        # Simulate restart with restored state
        new_state_machine = StateMachine(initial_state=current_state)

        if new_state_machine.get_current_state() != current_state:
            raise AssertionError
        if new_state_machine.get_current_state() != ApplicationState.RUNNING:
            raise AssertionError

    def test_callback_chain_execution(self):
        """Test execution of callback chains."""
        state_machine = StateMachine()

        execution_order = []

        def callback1(*args, **kwargs):
            execution_order.append("callback1")

        def callback2(*args, **kwargs):
            execution_order.append("callback2")

        def callback3(*args, **kwargs):
            execution_order.append("callback3")

        # Register multiple callbacks for same state
        state_machine.on_enter(ApplicationState.STARTING, callback1)
        state_machine.on_enter(ApplicationState.STARTING, callback2)
        state_machine.on_transition(callback3)

        # Perform transition
        state_machine.transition_to(ApplicationState.STARTING)

        # All callbacks should execute
        if "callback1" not in execution_order:
            raise AssertionError
        if "callback2" not in execution_order:
            raise AssertionError
        if "callback3" not in execution_order:
            raise AssertionError
        assert len(execution_order) == 3

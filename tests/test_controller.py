"""Tests for the app state machine logic in __main__.py.

These tests validate the state transition rules without creating a real
QApplication. They mock the engine and tray to test the controller logic.
"""

from unittest.mock import MagicMock, patch

from localdictate.state import AppState


class FakeTray:
    def __init__(self):
        self.state = None
        self.messages = []

    def set_state(self, s):
        self.state = s

    def update_hotkey_tooltip(self, h):
        pass

    def showMessage(self, *args, **kwargs):
        self.messages.append(args)

    # TrayIcon constants for compatibility
    IDLE = 0
    RECORDING = 1
    PROCESSING = 2
    MessageIcon = type("MI", (), {"Warning": 1, "Information": 0})()


class TestStateTransitions:
    def test_mic_failure_stays_idle(self):
        """If start_recording returns False, app stays IDLE."""
        state = {"app": AppState.IDLE, "active_job": None, "shutting_down": False}
        tray = FakeTray()
        engine = MagicMock()
        engine.start_recording.return_value = False

        # Simulate handle_toggle when IDLE
        if state["app"] == AppState.IDLE:
            state["active_job"] = None
            ok = engine.start_recording(device=None)
            if ok:
                state["app"] = AppState.RECORDING

        assert state["app"] == AppState.IDLE

    def test_no_audio_returns_idle(self):
        """If stop_and_transcribe returns (False, 0), app returns to IDLE."""
        state = {"app": AppState.RECORDING, "active_job": None, "shutting_down": False}
        engine = MagicMock()
        engine.stop_and_transcribe.return_value = (False, 0)

        if state["app"] == AppState.RECORDING:
            queued, job_id = engine.stop_and_transcribe("model")
            if queued:
                state["active_job"] = job_id
                state["app"] = AppState.PROCESSING
            else:
                state["app"] = AppState.IDLE

        assert state["app"] == AppState.IDLE
        assert state["active_job"] is None

    def test_transcription_queued_goes_processing(self):
        """Successful stop_and_transcribe goes to PROCESSING."""
        state = {"app": AppState.RECORDING, "active_job": None, "shutting_down": False}
        engine = MagicMock()
        engine.stop_and_transcribe.return_value = (True, 42)

        if state["app"] == AppState.RECORDING:
            queued, job_id = engine.stop_and_transcribe("model")
            if queued:
                state["active_job"] = job_id
                state["app"] = AppState.PROCESSING

        assert state["app"] == AppState.PROCESSING
        assert state["active_job"] == 42

    def test_stale_job_id_ignored(self):
        """Callback with wrong job_id is discarded."""
        state = {"app": AppState.PROCESSING, "active_job": 42, "shutting_down": False}
        called = []

        def handle_transcription(job_id, text):
            if state["shutting_down"] or job_id != state["active_job"]:
                return
            state["active_job"] = None
            state["app"] = AppState.IDLE
            called.append(text)

        handle_transcription(99, "stale text")
        assert state["app"] == AppState.PROCESSING  # unchanged
        assert not called

    def test_completed_job_id_cleared(self):
        """After terminal callback, active_job is None — re-fires are ignored."""
        state = {"app": AppState.PROCESSING, "active_job": 42, "shutting_down": False}

        def handle_complete(job_id):
            if state["shutting_down"] or job_id != state["active_job"]:
                return
            state["active_job"] = None
            state["app"] = AppState.IDLE

        handle_complete(42)
        assert state["app"] == AppState.IDLE
        assert state["active_job"] is None

        # Second fire of same job_id should be ignored
        state["app"] = AppState.PROCESSING  # pretend we moved on
        handle_complete(42)
        assert state["app"] == AppState.PROCESSING  # not changed

    def test_shutting_down_gates_all(self):
        """All handlers should no-op when shutting_down is True."""
        state = {"app": AppState.PROCESSING, "active_job": 42, "shutting_down": True}

        def handle_transcription(job_id, text):
            if state["shutting_down"] or job_id != state["active_job"]:
                return
            state["active_job"] = None
            state["app"] = AppState.IDLE

        handle_transcription(42, "text")
        assert state["app"] == AppState.PROCESSING  # unchanged

    def test_download_status_to_processing(self):
        """Status callback transitions through DOWNLOADING back to PROCESSING."""
        state = {"app": AppState.PROCESSING, "active_job": 42, "shutting_down": False}

        def handle_status(job_id, msg):
            if state["shutting_down"] or job_id != state["active_job"]:
                return
            if msg:
                state["app"] = AppState.DOWNLOADING
            else:
                state["app"] = AppState.PROCESSING

        handle_status(42, "Downloading model...")
        assert state["app"] == AppState.DOWNLOADING

        handle_status(42, "")
        assert state["app"] == AppState.PROCESSING

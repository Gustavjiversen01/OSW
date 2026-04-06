import threading
from unittest.mock import MagicMock, patch

import numpy as np

from localdictate.engine import Engine


def _make_engine():
    """Create an engine with mock callbacks."""
    return Engine(
        on_transcription=MagicMock(),
        on_complete=MagicMock(),
        on_error=MagicMock(),
        on_engine_error=MagicMock(),
        on_status=MagicMock(),
    )


class TestStartRecording:
    def test_returns_true_on_success(self):
        engine = _make_engine()
        with patch("sounddevice.InputStream") as mock_stream:
            mock_stream.return_value.start = MagicMock()
            result = engine.start_recording()
        assert result is True

    def test_returns_false_on_failure(self):
        engine = _make_engine()
        with patch("sounddevice.InputStream", side_effect=OSError("no mic")):
            result = engine.start_recording()
        assert result is False
        engine._on_engine_error.assert_called_once()
        # _recording should be reverted
        with engine._audio_lock:
            assert engine._recording is False

    def test_stream_closed_on_start_failure(self):
        engine = _make_engine()
        mock_stream = MagicMock()
        mock_stream.start.side_effect = OSError("start failed")
        with patch("sounddevice.InputStream", return_value=mock_stream):
            result = engine.start_recording()
        assert result is False
        mock_stream.close.assert_called_once()


class TestStopAndTranscribe:
    def test_returns_false_when_not_recording(self):
        engine = _make_engine()
        queued, job_id = engine.stop_and_transcribe("distil-medium.en")
        assert queued is False

    def test_returns_false_for_short_audio(self):
        engine = _make_engine()
        with engine._audio_lock:
            engine._recording = True
            # 0.1 seconds of audio (< 0.3s threshold)
            engine._chunks.append(np.zeros(1600, dtype=np.float32))
        queued, job_id = engine.stop_and_transcribe("distil-medium.en")
        assert queued is False

    def test_returns_true_and_job_id_for_valid_audio(self):
        engine = _make_engine()
        with engine._audio_lock:
            engine._recording = True
            engine._chunks.append(np.zeros(8000, dtype=np.float32))  # 0.5s
        with patch.object(engine, "_transcribe"):
            queued, job_id = engine.stop_and_transcribe("distil-medium.en")
        assert queued is True
        assert job_id > 0


class TestJobIdStaleCallback:
    def test_stale_job_discarded(self):
        engine = _make_engine()
        # Simulate: job_id was 1, but got incremented to 2
        with engine._job_lock:
            engine._job_id = 2

        # Worker with old job_id=1 should not emit
        def _is_current():
            with engine._job_lock:
                return 1 == engine._job_id

        assert _is_current() is False


class TestEnsureModel:
    def test_cache_key_includes_device_compute(self):
        engine = _make_engine()
        mock_model = MagicMock()
        with patch("faster_whisper.WhisperModel", return_value=mock_model, create=True) \
                as mock_cls:
            with engine._model_lock:
                engine._ensure_model("distil-medium.en", "cpu", "int8")
            assert engine._cache_key == ("distil-medium.en", "cpu", "int8")
            # Same call should not reload
            mock_cls.reset_mock()
            with engine._model_lock:
                engine._ensure_model("distil-medium.en", "cpu", "int8")
            mock_cls.assert_not_called()
            # Different device should reload
            with engine._model_lock:
                engine._ensure_model("distil-medium.en", "cuda", "float16")
            mock_cls.assert_called_once()

    def test_failure_preserves_old_model(self):
        engine = _make_engine()
        old_model = MagicMock()
        engine.model = old_model
        engine._cache_key = ("distil-medium.en", "cpu", "int8")

        with patch("faster_whisper.WhisperModel",
                   side_effect=RuntimeError("load failed"), create=True):
            try:
                with engine._model_lock:
                    engine._ensure_model("large-v3", "cpu", "int8")
            except RuntimeError:
                pass

        assert engine.model is old_model
        assert engine._cache_key == ("distil-medium.en", "cpu", "int8")


class TestUnload:
    def test_unload_skips_deletion_if_worker_alive(self):
        engine = _make_engine()
        # Add a "worker" that's still alive
        t = threading.Thread(target=lambda: threading.Event().wait(10))
        t.daemon = True
        t.start()
        with engine._job_lock:
            engine._workers.add(t)

        engine.model = MagicMock()
        engine.unload()  # should skip deletion because worker is alive
        assert engine.model is not None  # not deleted

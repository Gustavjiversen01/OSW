import gc
import threading
import time
from collections import deque

import numpy as np

from . import settings
from .cache import is_model_cached


class Engine:
    """Audio recording and Whisper transcription engine.

    Thread safety:
      - _audio_lock: protects _recording and _chunks (main ↔ callback thread)
      - _model_lock: protects model and _cache_key (held during model load by
        workers; main thread only acquires after joining workers in unload())
      - _job_lock: protects _job_id and _workers (main ↔ worker thread)

    Rule: _audio_lock and _job_lock are never held during I/O or joins.
    _model_lock may be held during model load (by workers only, by design).
    """

    def __init__(self, on_transcription, on_complete, on_error,
                 on_engine_error, on_status):
        self._on_transcription = on_transcription  # (job_id, text)
        self._on_complete = on_complete              # (job_id,)
        self._on_error = on_error                    # (job_id, msg)
        self._on_engine_error = on_engine_error      # (msg,) non-job-scoped
        self._on_status = on_status                  # (job_id, msg)

        self.model = None
        self._cache_key = None  # (model_name, device, compute_type)

        self._chunks: deque[np.ndarray] = deque()
        self._stream = None
        self._recording = False

        self._audio_lock = threading.Lock()
        self._model_lock = threading.Lock()
        self._job_lock = threading.Lock()
        self._job_id = 0
        self._workers: set[threading.Thread] = set()

    # -- Public API (called from Qt main thread) --

    def start_recording(self, device=None) -> bool:
        """Start recording audio. Returns True on success."""
        with self._job_lock:
            self._job_id += 1  # invalidate stale transcriptions

        with self._audio_lock:
            self._chunks.clear()
            self._recording = True

        stream = None
        try:
            import sounddevice as sd
            stream = sd.InputStream(
                samplerate=16000, channels=1, dtype="float32",
                device=device, callback=self._audio_callback,
            )
            stream.start()
        except Exception as e:
            with self._audio_lock:
                self._recording = False
            if stream:
                try:
                    stream.close()
                except Exception:
                    pass
            self._on_engine_error(f"Microphone error: {e}")
            return False

        with self._audio_lock:
            self._stream = stream
        return True

    def stop_and_transcribe(self, model_name: str, initial_prompt=None,
                            length_penalty=1.0, language=None,
                            device="auto", compute_type="default",
                            ) -> tuple[bool, int]:
        """Stop recording and start transcription. Returns (queued, job_id)."""
        with self._audio_lock:
            if not self._recording:
                return (False, 0)
            self._recording = False
            chunks = list(self._chunks)
            self._chunks.clear()
            stream = self._stream
            self._stream = None

        if stream:
            try:
                stream.stop()
                stream.close()
            except Exception:
                pass

        if not chunks:
            return (False, 0)

        audio = np.concatenate(chunks).flatten()
        if len(audio) / 16000 < 0.3:
            return (False, 0)

        with self._job_lock:
            self._job_id += 1
            my_job = self._job_id
            t = threading.Thread(
                target=self._transcribe,
                args=(audio, model_name, initial_prompt, length_penalty,
                      language, device, compute_type, my_job),
                daemon=True,
            )
            self._workers.add(t)
            t.start()

        return (True, my_job)

    def cancel(self):
        """Cancel any active recording and invalidate in-flight jobs."""
        with self._audio_lock:
            self._recording = False
            self._chunks.clear()
            stream = self._stream
            self._stream = None

        if stream:
            try:
                stream.stop()
                stream.close()
            except Exception:
                pass

        with self._job_lock:
            self._job_id += 1

        self._join_workers(timeout=5)

    def unload(self):
        """Release model and wait for workers. Safe to call on quit."""
        with self._job_lock:
            self._job_id += 1
            any_alive = any(w.is_alive() for w in self._workers)

        # Only join if workers are still alive (cancel() may have already joined)
        if any_alive:
            self._join_workers(timeout=3)
            with self._job_lock:
                any_alive = any(w.is_alive() for w in self._workers)

        if any_alive:
            return  # skip model deletion, rely on process exit

        if not self._model_lock.acquire(timeout=2):
            return  # lock held by lingering worker, skip
        try:
            if self.model:
                del self.model
                gc.collect()
            self.model = None
            self._cache_key = None
        finally:
            self._model_lock.release()

    # -- Worker (runs on daemon thread) --

    def _transcribe(self, audio: np.ndarray, model_name: str,
                    initial_prompt, length_penalty, language,
                    device, compute_type, job_id: int):
        def _is_current():
            with self._job_lock:
                return job_id == self._job_id

        try:
            with self._model_lock:
                if not _is_current():
                    return

                # Download status
                if not is_model_cached(model_name):
                    if _is_current():
                        self._on_status(job_id, "Downloading model...")

                try:
                    self._ensure_model(model_name, device, compute_type)
                finally:
                    if _is_current():
                        self._on_status(job_id, "")

                if not _is_current():
                    return

                # Resolve language for English-only models
                effective_language = language
                if language is None and model_name in settings.ENGLISH_ONLY_MODELS:
                    effective_language = "en"
                elif language and language != "en" and model_name in settings.ENGLISH_ONLY_MODELS:
                    if _is_current():
                        self._on_error(
                            job_id,
                            f"Model '{model_name}' only supports English. "
                            "Switch to High or Maximum for multilingual.",
                        )
                    return

                segments, _ = self.model.transcribe(
                    audio, language=effective_language, beam_size=5,
                    vad_filter=False, initial_prompt=initial_prompt,
                    length_penalty=length_penalty,
                )
                text = " ".join(seg.text.strip() for seg in segments).strip()

            # Outside model lock — emit callbacks
            if _is_current():
                if text:
                    self._on_transcription(job_id, text)
                else:
                    self._on_complete(job_id)

        except Exception as e:
            if _is_current():
                self._on_error(job_id, f"Transcription error: {e}")
        finally:
            with self._job_lock:
                self._workers.discard(threading.current_thread())

    def _ensure_model(self, model_name: str, device: str, compute_type: str):
        """Load model if needed. Must be called under _model_lock."""
        cache_key = (model_name, device, compute_type)
        if self.model and self._cache_key == cache_key:
            return

        from faster_whisper import WhisperModel

        # Resolve auto device/compute
        resolved_device = device
        resolved_compute = compute_type
        if device == "auto" or compute_type == "default":
            try:
                import ctranslate2
                has_cuda = ctranslate2.get_cuda_device_count() > 0
            except Exception:
                has_cuda = False
            if device == "auto":
                resolved_device = "cuda" if has_cuda else "cpu"
            if compute_type == "default":
                resolved_compute = "float16" if resolved_device == "cuda" else "int8"

        actual_device = resolved_device
        actual_compute = resolved_compute
        try:
            new_model = WhisperModel(
                model_name, device=resolved_device,
                compute_type=resolved_compute,
            )
        except Exception as e:
            # GPU fallback: only retry CPU when device was "auto"
            if device == "auto" and "cuda" in str(e).lower():
                actual_device = "cpu"
                actual_compute = "int8"
                new_model = WhisperModel(
                    model_name, device="cpu", compute_type="int8",
                )
            else:
                raise

        # Success — swap models, cache key uses actual resolved values
        old = self.model
        self.model = new_model
        self._cache_key = (model_name, actual_device, actual_compute)
        if old:
            del old
            gc.collect()

    def _audio_callback(self, indata, frames, time_info, status):
        with self._audio_lock:
            if self._recording:
                self._chunks.append(indata.copy())

    # -- Helpers --

    def _join_workers(self, timeout=5):
        """Join all tracked workers with a shared deadline."""
        deadline = time.monotonic() + timeout
        with self._job_lock:
            workers = list(self._workers)
        for w in workers:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            w.join(timeout=remaining)

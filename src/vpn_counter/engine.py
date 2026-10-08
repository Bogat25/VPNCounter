from __future__ import annotations

import math
import threading
import time
from dataclasses import dataclass

import numpy as np
from PySide6.QtCore import QThread, Signal
from scipy.signal import resample_poly

from vpn_counter.audio import AudioBuffer
from vpn_counter.downloads import download_model
from vpn_counter.matching import RecognitionBatch, SpeechWord
from vpn_counter.runtime import (
    audio_thread_context,
    configure_gpu_libraries,
    configure_model_storage,
)
from vpn_counter.settings import data_directory


@dataclass(frozen=True, slots=True)
class Microphone:
    index: int
    label: str
    sample_rate: int


def microphones() -> list[Microphone]:
    import sounddevice as sd

    devices = sd.query_devices()
    hosts = sd.query_hostapis()
    inputs = [
        Microphone(
            index,
            f"{device['name']} · {hosts[device['hostapi']]['name']}",
            int(device["default_samplerate"]),
        )
        for index, device in enumerate(devices)
        if device["max_input_channels"] > 0
    ]
    wasapi = [device for device in inputs if "WASAPI" in device.label]
    return wasapi or inputs


@dataclass(frozen=True, slots=True)
class EngineOptions:
    model: str = "large-v3"
    device: str = "cuda"
    microphone_index: int | None = None


def load_model(
    options: EngineOptions, notify=lambda _message: None, progress=lambda _percent: None
):
    configure_model_storage()
    configure_gpu_libraries()
    import ctranslate2
    from faster_whisper import WhisperModel

    if options.device == "cuda" and ctranslate2.get_cuda_device_count() == 0:
        raise RuntimeError("No CUDA GPU is available. Select CPU fallback or run setup again.")
    model_directory = data_directory() / "models" / options.model
    required = ("model.bin", "config.json", "tokenizer.json", "vocabulary.json")
    cached = all((model_directory / filename).is_file() for filename in required)
    if not cached:
        notify("Downloading model · first setup can take several minutes")
    model_path = (
        str(model_directory) if cached else download_model(options.model, model_directory, progress)
    )
    notify("Loading speech model")
    model = WhisperModel(
        model_path,
        device=options.device,
        compute_type="float16" if options.device == "cuda" else "int8",
        num_workers=1,
        cpu_threads=4,
    )
    notify("Warming up recognition")
    segments, _ = model.transcribe(np.zeros(16000, dtype=np.float32), language="hu", beam_size=1)
    list(segments)  # Inference is lazy; this also checks CUDA/cuDNN compatibility.
    return model


def transcribe_window(model, samples: np.ndarray, offset: float = 0.0):
    segments, _ = model.transcribe(
        samples,
        language="hu",
        task="transcribe",
        beam_size=5,
        temperature=0.0,
        condition_on_previous_text=False,
        word_timestamps=True,
        vad_filter=True,
        vad_parameters={
            "min_speech_duration_ms": 100,
            "min_silence_duration_ms": 250,
            "speech_pad_ms": 200,
        },
        # Decode ordinary Hungarian speech without suggesting the target word.
        # Keyword-only hotwords can turn unclear audio into false VPN mentions.
        hallucination_silence_threshold=1.0,
    )
    words: list[SpeechWord] = []
    texts: list[str] = []
    for segment in segments:
        if segment.no_speech_prob > 0.6 or segment.avg_logprob < -1.0:
            continue
        texts.append(segment.text.strip())
        words.extend(
            SpeechWord(word.word, offset + word.start, offset + word.end, word.probability)
            for word in segment.words or ()
        )
    return tuple(words), " ".join(texts)


class SpeechWorker(QThread):
    status = Signal(str)
    download_progress = Signal(int)
    listening = Signal()
    batch_ready = Signal(object)
    failed = Signal(str)
    warning = Signal(str)

    def __init__(self, options: EngineOptions, parent=None) -> None:
        super().__init__(parent)
        self.options = options
        self._stop = threading.Event()
        self._paused = threading.Event()
        self._buffer: AudioBuffer | None = None
        self._control_lock = threading.Lock()
        self._requested_generation = 0

    @property
    def level(self) -> float:
        return self._buffer.level if self._buffer and not self._paused.is_set() else 0.0

    @property
    def generation(self) -> int:
        return self._buffer.generation if self._buffer else self._requested_generation

    def invalidate(self) -> None:
        with self._control_lock:
            self._requested_generation += 1
            if self._buffer:
                self._buffer.clear()

    def pause(self) -> None:
        self._paused.set()
        self.invalidate()

    def resume(self) -> None:
        self.invalidate()
        self._paused.clear()

    def stop(self) -> None:
        self._stop.set()
        self.invalidate()

    def run(self) -> None:
        try:
            self.status.emit("Preparing recognition")
            model = load_model(self.options, self.status.emit, self.download_progress.emit)
            if self._stop.is_set():
                return
            with audio_thread_context():
                self._listen(model)
        except Exception as error:
            if not self._stop.is_set():
                detail = str(error)
                if any(term in detail.lower() for term in ("cublas", "cudnn", "cuda", "dll")):
                    detail += (
                        "\nRun scripts/setup.ps1 to prepare GPU libraries, or select CPU fallback."
                    )
                self.failed.emit(detail)

    def _listen(self, model) -> None:
        import sounddevice as sd

        info = sd.query_devices(self.options.microphone_index, "input")
        rate = int(info["default_samplerate"])
        try:
            sd.check_input_settings(
                device=self.options.microphone_index, channels=1, dtype="float32", samplerate=16000
            )
            rate = 16000
        except sd.PortAudioError:
            pass
        self._buffer = AudioBuffer(rate)

        def callback(indata, _frames, _timing, status) -> None:
            if not self._paused.is_set() and not self._stop.is_set():
                self._buffer.append(indata[:, 0], overflow=bool(status.input_overflow))

        stream = sd.InputStream(
            device=self.options.microphone_index,
            channels=1,
            samplerate=rate,
            dtype="float32",
            callback=callback,
        )
        with stream:
            self.listening.emit()
            self.status.emit("Listening")
            generation = -1
            next_end = 0
            last_warning = -1
            stream_paused = False
            while not self._stop.is_set():
                if self._paused.is_set():
                    if not stream_paused:
                        stream.stop()
                        stream_paused = True
                    self._stop.wait(0.08)
                    continue
                if stream_paused:
                    stream.start()
                    stream_paused = False
                start, end, current_generation = self._buffer.bounds
                if current_generation != generation:
                    generation = current_generation
                    next_end = start + 3 * rate
                if self._buffer.overflows != last_warning:
                    last_warning = self._buffer.overflows
                    if last_warning:
                        self.warning.emit("Microphone overflow · an audio segment was lost")
                if next_end < start:
                    self.warning.emit("Recognition fell behind · reduce model size for this device")
                    self.invalidate()
                    continue
                if end < next_end:
                    self._stop.wait(0.05)
                    continue
                window = self._buffer.window(next_end, seconds=6)
                next_end += 2 * rate
                if window is None:
                    continue
                samples = window.samples
                if rate != 16000:
                    divisor = math.gcd(rate, 16000)
                    samples = resample_poly(samples, 16000 // divisor, rate // divisor).astype(
                        np.float32
                    )
                before = time.perf_counter()
                words, text = transcribe_window(model, samples, window.start_sample / rate)
                elapsed = time.perf_counter() - before
                if (
                    not self._stop.is_set()
                    and not self._paused.is_set()
                    and window.generation == self.generation
                ):
                    # A short trailing guard lets incomplete letter sequences be
                    # observed in the next overlapping window before committing.
                    stable_end = window.end_sample / rate - 0.25
                    stable_words = tuple(word for word in words if word.end <= stable_end)
                    self.batch_ready.emit(
                        RecognitionBatch(
                            stable_words,
                            text,
                            window.generation,
                            window.end_sample / rate,
                            elapsed,
                        )
                    )

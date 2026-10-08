from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class AudioWindow:
    samples: np.ndarray
    start_sample: int
    end_sample: int
    generation: int


class AudioBuffer:
    """Bounded microphone history addressed by absolute sample positions."""

    def __init__(self, sample_rate: int, seconds: int = 30) -> None:
        self.sample_rate = sample_rate
        self.capacity = sample_rate * seconds
        self._blocks: deque[np.ndarray] = deque()
        self._size = 0
        self._total = 0
        self._generation = 0
        self._lock = threading.Lock()
        self.level = 0.0
        self.overflows = 0

    @property
    def generation(self) -> int:
        with self._lock:
            return self._generation

    @property
    def bounds(self) -> tuple[int, int, int]:
        with self._lock:
            return self._total - self._size, self._total, self._generation

    def clear(self) -> int:
        with self._lock:
            self._blocks.clear()
            self._size = 0
            self._generation += 1
            self.level = 0.0
            return self._generation

    def append(self, samples: np.ndarray, overflow: bool = False) -> None:
        block = np.asarray(samples, dtype=np.float32).reshape(-1).copy()
        if not len(block):
            return
        self.level = min(1.0, float(np.sqrt(np.mean(block * block))) * 6)
        with self._lock:
            if overflow:
                self._blocks.clear()
                self._size = 0
                self._generation += 1
                self.overflows += 1
            self._blocks.append(block)
            self._size += len(block)
            self._total += len(block)
            while self._size > self.capacity and self._blocks:
                excess = self._size - self.capacity
                first = self._blocks[0]
                if len(first) <= excess:
                    self._size -= len(self._blocks.popleft())
                else:
                    self._blocks[0] = first[excess:]
                    self._size -= excess

    def window(self, end_sample: int, seconds: float) -> AudioWindow | None:
        with self._lock:
            earliest = self._total - self._size
            if end_sample > self._total or end_sample <= earliest or not self._blocks:
                return None
            start = max(earliest, end_sample - int(seconds * self.sample_rate))
            joined = np.concatenate(tuple(self._blocks))
            samples = joined[start - earliest : end_sample - earliest].copy()
            return AudioWindow(samples, start, end_sample, self._generation)

import queue
import threading

import numpy as np
import soundcard as sc


class AudioCapture:
    def __init__(self, sample_rate=16000, chunk_seconds=2.0, device_substr="speakers"):
        self.sample_rate = sample_rate
        self.chunk_seconds = chunk_seconds
        self.frames_per_buffer = int(sample_rate * chunk_seconds)
        self.device_substr = device_substr
        self.q: queue.Queue[np.ndarray] = queue.Queue(maxsize=4)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def _find_device(self):
        mics = sc.all_microphones(include_loopback=True)
        for mic in mics:
            if self.device_substr.lower() in mic.name.lower():
                return mic
        raise RuntimeError(
            "No loopback audio device matching '%s'. Check Windows Sound settings." % self.device_substr
        )

    def _worker(self):
        mic = self._find_device()
        with mic.recorder(samplerate=self.sample_rate, channels=1) as rec:
            while not self._stop.is_set():
                try:
                    data = rec.record(numframes=self.frames_per_buffer)
                except Exception:
                    continue
                if data.size == 0:
                    continue
                # shape: (frames, channels) -> mono float32
                mono = np.ascontiguousarray(data[:, 0], dtype=np.float32)
                # trim tail if short
                if mono.shape[0] < self.frames_per_buffer:
                    mono = np.pad(mono, (0, self.frames_per_buffer - mono.shape[0]))
                try:
                    self.q.put_nowait(mono)
                except queue.Full:
                    try:
                        self.q.get_nowait()
                    except queue.Empty:
                        pass
                    self.q.put_nowait(mono)

    def start(self):
        self._stop.clear()
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def read(self) -> np.ndarray | None:
        try:
            return self.q.get_nowait()
        except queue.Empty:
            return None

    def stop(self):
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1)

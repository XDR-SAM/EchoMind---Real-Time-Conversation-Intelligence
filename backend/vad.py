import numpy as np


class EnergyVAD:
    def __init__(self, sample_rate=16000, frame_ms=30, energy_floor=0.008, hangover_frames=6):
        self.frame_size = int(sample_rate * frame_ms / 1000)
        self.energy_floor = energy_floor
        self.hangover = hangover_frames
        self._hangover_counter = 0
        self._speech_active = False

    def __call__(self, chunk: np.ndarray) -> bool:
        speech = bool(np.sqrt(np.mean(chunk.astype(np.float32) ** 2)) > self.energy_floor)
        if speech:
            self._hangover_counter = self.hangover
            self._speech_active = True
            return True
        if self._speech_active and self._hangover_counter > 0:
            self._hangover_counter -= 1
            return True
        self._speech_active = False
        return False

    def reset(self):
        self._speech_active = False
        self._hangover_counter = 0

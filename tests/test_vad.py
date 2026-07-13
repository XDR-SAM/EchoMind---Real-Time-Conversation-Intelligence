"""VAD behavior tests focused on EnergyVAD thresholds and hangover."""
from __future__ import annotations

from unittest import TestCase

import numpy as np

from backend.vad import EnergyVAD


class VADBehaviorTests(TestCase):
    def setUp(self):
        self.vad = EnergyVAD(energy_floor=0.01, frame_ms=30, sample_rate=16000)

    def test_silence_is_not_speech(self) -> None:
        silence = np.zeros(480, dtype=np.float32)
        self.assertFalse(self.vad(silence))

    def test_loud_tone_is_speech(self) -> None:
        loud = np.full(480, 0.5, dtype=np.float32)
        self.assertTrue(self.vad(loud))

    def test_hangover_extends_speech_detection(self) -> None:
        vad = EnergyVAD(energy_floor=0.5, frame_ms=30, sample_rate=16000, hangover_frames=3)
        loud = np.full(480, 0.9, dtype=np.float32)
        quiet = np.zeros(480, dtype=np.float32)
        self.assertTrue(vad(loud))
        self.assertTrue(vad(quiet))
        self.assertTrue(vad(quiet))
        self.assertTrue(vad(quiet))
        self.assertFalse(vad(quiet))

    def test_reset_clears_state(self) -> None:
        loud = np.full(480, 0.9, dtype=np.float32)
        quiet = np.zeros(480, dtype=np.float32)
        self.assertTrue(self.vad(loud))
        self.vad.reset()
        self.assertFalse(self.vad(quiet))

    def test_partial_chunk_does_not_crash(self) -> None:
        short = np.ones(160, dtype=np.float32)
        self.vad(short)

    def test_energy_floor_controls_sensitivity(self) -> None:
        rms = 0.02
        data = np.full(480, float(rms), dtype=np.float32)
        strict = EnergyVAD(energy_floor=rms + 0.001, frame_ms=30, sample_rate=16000, hangover_frames=0)
        lenient = EnergyVAD(energy_floor=rms - 0.001, frame_ms=30, sample_rate=16000, hangover_frames=0)
        self.assertFalse(strict(data))
        self.assertTrue(lenient(data))

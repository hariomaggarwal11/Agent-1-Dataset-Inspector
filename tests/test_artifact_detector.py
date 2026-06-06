"""Tests for artifact detection."""

import numpy as np
import pytest
import mne

from core.shared.artifact_detector import detect_eeg_artifacts, detect_ecg_artifacts


class TestEEGArtifacts:
    """Tests for EEG artifact detection."""

    def test_clean_signal(self, sample_eeg_raw):
        results = detect_eeg_artifacts(sample_eeg_raw)
        assert "flat_channels" in results
        assert "noisy_channels" in results
        assert "line_noise" in results

    def test_flat_channel_detected(self):
        """Test flat channel detection."""
        n_ch = 4
        fs = 256
        data = np.random.randn(n_ch, fs * 10) * 20e-6
        # Make one channel flat
        data[2] = 0.0

        info = mne.create_info(ch_names=[f"Ch{i}" for i in range(n_ch)],
                              sfreq=fs, ch_types="eeg")
        raw = mne.io.RawArray(data, info, verbose=False)

        results = detect_eeg_artifacts(raw)
        assert results["flat_channels"]["status"] == "fail"
        assert "Ch2" in results["flat_channels"]["channels"]

    def test_line_noise_detected(self):
        """Test 50 Hz line noise detection."""
        n_ch = 2
        fs = 256
        duration = 10
        n_samples = fs * duration
        t = np.arange(n_samples) / fs

        data = np.random.randn(n_ch, n_samples) * 10e-6
        # Add strong 50 Hz
        data += np.sin(2 * np.pi * 50 * t) * 100e-6

        info = mne.create_info(ch_names=[f"Ch{i}" for i in range(n_ch)],
                              sfreq=fs, ch_types="eeg")
        raw = mne.io.RawArray(data, info, verbose=False)

        results = detect_eeg_artifacts(raw)
        assert results["line_noise"]["status"] == "fail"


class TestECGArtifacts:
    """Tests for ECG artifact detection."""

    def test_returns_all_checks(self, sample_ecg_data):
        results = detect_ecg_artifacts(sample_ecg_data)
        assert "baseline_wander" in results
        assert "powerline_noise" in results
        assert "signal_clipping" in results
        assert "motion_artifacts" in results
        assert "lead_reversal" in results
        assert "missing_beats" in results
        assert "pacemaker_spikes" in results

    def test_clipping_detected(self):
        """Test signal clipping detection."""
        fs = 500
        n_samples = fs * 10
        sig = np.random.randn(n_samples)
        # Clip the signal
        sig = np.clip(sig, -2, 2)
        # Make many samples exactly at the clip level
        sig[:500] = 2.0

        ecg_data = {
            "signals": np.array([sig]),
            "fs": fs,
            "lead_names": ["II"],
        }
        results = detect_ecg_artifacts(ecg_data)
        assert results["signal_clipping"]["status"] == "fail"

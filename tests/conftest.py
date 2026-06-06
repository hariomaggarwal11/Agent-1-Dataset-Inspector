"""Shared test fixtures for NeuroInspect tests."""

import sys
import os
import tempfile

import numpy as np
import pytest
import mne

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def sample_eeg_raw():
    """Create a simple MNE Raw object for testing."""
    n_channels = 14
    fs = 128
    duration = 10  # seconds
    n_samples = fs * duration

    ch_names = ["AF3", "F7", "F3", "FC5", "T7", "P7", "O1",
                "O2", "P8", "T8", "FC6", "F4", "F8", "AF4"]
    data = np.random.randn(n_channels, n_samples) * 20e-6  # 20 uV typical EEG

    info = mne.create_info(ch_names=ch_names, sfreq=fs, ch_types="eeg")
    raw = mne.io.RawArray(data, info, verbose=False)
    return raw


@pytest.fixture
def sample_ecg_data():
    """Create sample ECG data dict for testing."""
    fs = 360
    duration = 30  # seconds
    n_samples = fs * duration
    t = np.arange(n_samples) / fs

    # Simulate ECG-like signal (simple sine + R-peaks)
    ecg_signal = np.sin(2 * np.pi * 1.2 * t)  # ~72 BPM baseline
    # Add R-peak-like spikes
    for peak_time in np.arange(0, duration, 0.833):  # ~72 BPM
        peak_sample = int(peak_time * fs)
        if peak_sample < n_samples:
            ecg_signal[peak_sample] = 3.0
            if peak_sample + 1 < n_samples:
                ecg_signal[peak_sample + 1] = -0.5

    return {
        "signals": np.array([ecg_signal, ecg_signal * 0.5]),  # 2 leads
        "fs": fs,
        "lead_names": ["MLII", "V1"],
        "units": ["mV", "mV"],
        "gain": [200.0, 200.0],
        "baseline": [0.0, 0.0],
        "duration_s": duration,
        "record_info": {"comments": [], "record_name": "test_record"},
        "annotations": None,
    }


@pytest.fixture
def temp_edf_file(sample_eeg_raw):
    """Create a temporary EDF file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".fif", delete=False) as f:
        sample_eeg_raw.save(f.name, overwrite=True, verbose=False)
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def temp_csv_ecg():
    """Create a temporary CSV ECG file for testing."""
    import pandas as pd

    fs = 500
    duration = 5
    n_samples = fs * duration
    t = np.arange(n_samples) / fs

    data = {
        "time": t,
        "Lead_I": np.sin(2 * np.pi * 1.0 * t) + np.random.randn(n_samples) * 0.1,
        "Lead_II": np.sin(2 * np.pi * 1.0 * t + 0.2) + np.random.randn(n_samples) * 0.1,
    }
    df = pd.DataFrame(data)

    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
        df.to_csv(f.name, index=False)
        yield f.name
    os.unlink(f.name)

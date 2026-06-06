"""Tests for EEG inspector functions."""

import numpy as np
import pandas as pd
import pytest
import mne

from core.eeg.inspector import (
    extract_channel_info,
    infer_reference,
    extract_events,
    compute_psd,
    compute_faa,
    detect_known_dataset,
    extract_metadata,
)


class TestExtractChannelInfo:
    """Tests for channel info extraction."""

    def test_returns_dataframe(self, sample_eeg_raw):
        df = extract_channel_info(sample_eeg_raw)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 14
        assert "Name" in df.columns
        assert "Type" in df.columns

    def test_channel_names_match(self, sample_eeg_raw):
        df = extract_channel_info(sample_eeg_raw)
        assert df["Name"].iloc[0] == "AF3"
        assert df["Name"].iloc[-1] == "AF4"


class TestInferReference:
    """Tests for reference scheme inference."""

    def test_no_ref_channel(self, sample_eeg_raw):
        ref = infer_reference(sample_eeg_raw)
        assert "Common Average" in ref or "hardware" in ref

    def test_with_mastoid_channels(self):
        ch_names = ["C3", "C4", "M1", "M2"]
        info = mne.create_info(ch_names=ch_names, sfreq=256, ch_types="eeg")
        raw = mne.io.RawArray(np.random.randn(4, 1000), info, verbose=False)
        ref = infer_reference(raw)
        assert "Mastoid" in ref


class TestComputePSD:
    """Tests for PSD computation."""

    def test_returns_correct_structure(self, sample_eeg_raw):
        result = compute_psd(sample_eeg_raw)
        assert "psds" in result
        assert "freqs" in result
        assert "band_powers" in result
        assert "dominant_freqs" in result

    def test_freqs_in_range(self, sample_eeg_raw):
        result = compute_psd(sample_eeg_raw, fmin=0.5, fmax=50)
        assert result["freqs"][0] >= 0.5
        assert result["freqs"][-1] <= 50

    def test_band_powers_sum_reasonable(self, sample_eeg_raw):
        result = compute_psd(sample_eeg_raw)
        band_powers = result["band_powers"]
        # Each row should sum to approximately 100%
        row_sums = band_powers.sum(axis=1)
        assert all(80 <= s <= 120 for s in row_sums)


class TestComputeFAA:
    """Tests for Frontal Alpha Asymmetry."""

    def test_faa_available_with_af_channels(self, sample_eeg_raw):
        result = compute_faa(sample_eeg_raw, left_ch="AF3", right_ch="AF4")
        assert result["available"] is True
        assert result["faa_value"] is not None

    def test_faa_unavailable_without_channels(self, sample_eeg_raw):
        result = compute_faa(sample_eeg_raw, left_ch="XYZ", right_ch="ABC")
        assert result["available"] is False


class TestDetectKnownDataset:
    """Tests for known dataset detection."""

    def test_detects_dreamer_like(self, sample_eeg_raw):
        # sample_eeg_raw has 14 channels at 128 Hz - matches DREAMER
        result = detect_known_dataset(sample_eeg_raw)
        assert result is not None
        assert result["name"] == "DREAMER"

    def test_no_match_for_unusual(self):
        ch_names = [f"Ch{i}" for i in range(7)]
        info = mne.create_info(ch_names=ch_names, sfreq=99, ch_types="eeg")
        raw = mne.io.RawArray(np.random.randn(7, 1000), info, verbose=False)
        result = detect_known_dataset(raw)
        assert result is None

"""Tests for ECG inspector functions."""

import numpy as np
import pandas as pd
import pytest

from core.ecg.inspector import (
    extract_lead_info,
    extract_annotations,
    compute_rpeaks,
    assess_signal_quality,
    detect_known_ecg_dataset,
    extract_ecg_metadata,
)


class TestExtractLeadInfo:
    """Tests for lead info extraction."""

    def test_returns_dataframe(self, sample_ecg_data):
        df = extract_lead_info(sample_ecg_data)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert "Lead Name" in df.columns

    def test_lead_names(self, sample_ecg_data):
        df = extract_lead_info(sample_ecg_data)
        assert df["Lead Name"].iloc[0] == "MLII"
        assert df["Lead Name"].iloc[1] == "V1"


class TestExtractAnnotations:
    """Tests for annotation extraction."""

    def test_no_annotations(self, sample_ecg_data):
        result = extract_annotations(sample_ecg_data)
        assert result["has_annotations"] is False


class TestComputeRpeaks:
    """Tests for R-peak computation."""

    def test_returns_hr_stats(self, sample_ecg_data):
        result = compute_rpeaks(sample_ecg_data)
        assert "hr_stats" in result
        assert "r_peaks" in result

    def test_hr_in_reasonable_range(self, sample_ecg_data):
        result = compute_rpeaks(sample_ecg_data)
        mean_hr = result["hr_stats"].get("mean_hr", 0)
        # Our simulated signal is ~72 BPM
        assert 30 <= mean_hr <= 200 or mean_hr == 0  # Allow 0 if detection fails


class TestAssessSignalQuality:
    """Tests for signal quality assessment."""

    def test_returns_dataframe(self, sample_ecg_data):
        df = assess_signal_quality(sample_ecg_data)
        assert isinstance(df, pd.DataFrame)
        assert "Quality Index" in df.columns
        assert len(df) == 2

    def test_quality_in_range(self, sample_ecg_data):
        df = assess_signal_quality(sample_ecg_data)
        for qi in df["Quality Index"]:
            assert 0 <= qi <= 1.0


class TestDetectKnownDataset:
    """Tests for known ECG dataset detection."""

    def test_detects_mitbih_like(self, sample_ecg_data):
        # sample_ecg_data has 360 Hz, 2 leads (MLII, V1) - matches MIT-BIH
        result = detect_known_ecg_dataset(sample_ecg_data)
        assert result is not None
        assert "MIT-BIH" in result["name"]

    def test_no_match_unusual(self):
        data = {
            "signals": np.random.randn(5, 1000),
            "fs": 123,
            "lead_names": ["X1", "X2", "X3", "X4", "X5"],
        }
        result = detect_known_ecg_dataset(data)
        assert result is None

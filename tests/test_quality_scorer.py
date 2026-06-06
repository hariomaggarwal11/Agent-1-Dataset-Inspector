"""Tests for quality scoring functions."""

import numpy as np
import pandas as pd
import pytest

from core.eeg.report_builder import compute_eeg_quality_score
from core.ecg.report_builder import compute_ecg_quality_score


class TestEEGQualityScore:
    """Tests for EEG quality score computation."""

    def test_perfect_score(self):
        """Test a 'perfect' report gets high score."""
        report = {
            "metadata": {
                "Sampling Frequency": "256 Hz",
                "Number of Channels": 32,
                "Duration": "10 min 0 s",
            },
            "channel_info": pd.DataFrame({"Has Location": [True] * 32}),
            "events": {"has_events": True},
            "artifacts": {
                "flat_channels": {"status": "pass"},
                "line_noise": {"status": "pass"},
                "eog_artifacts": {"status": "pass"},
                "emg_artifacts": {"status": "pass"},
            },
        }
        result = compute_eeg_quality_score(report)
        assert result["score"] >= 85
        assert result["max_score"] == 100

    def test_low_score_with_issues(self):
        """Test a noisy report gets low score."""
        report = {
            "metadata": {
                "Sampling Frequency": "64 Hz",
                "Number of Channels": 4,
                "Duration": "2 min 0 s",
            },
            "channel_info": pd.DataFrame({"Has Location": [False] * 4}),
            "events": {"has_events": False},
            "artifacts": {
                "flat_channels": {"status": "fail"},
                "line_noise": {"status": "fail"},
                "eog_artifacts": {"status": "warn"},
                "emg_artifacts": {"status": "warn"},
            },
        }
        result = compute_eeg_quality_score(report)
        assert result["score"] < 40

    def test_breakdown_included(self):
        """Test that breakdown is included."""
        report = {
            "metadata": {"Sampling Frequency": "128 Hz", "Number of Channels": 8, "Duration": "5 min 0 s"},
            "channel_info": pd.DataFrame({"Has Location": [True]}),
            "events": {"has_events": True},
            "artifacts": {
                "flat_channels": {"status": "pass"},
                "line_noise": {"status": "pass"},
                "eog_artifacts": {"status": "pass"},
                "emg_artifacts": {"status": "pass"},
            },
        }
        result = compute_eeg_quality_score(report)
        assert "breakdown" in result
        assert len(result["breakdown"]) > 0


class TestECGQualityScore:
    """Tests for ECG quality score computation."""

    def test_perfect_ecg_score(self):
        """Test a 'perfect' ECG report."""
        report = {
            "metadata": {
                "Sampling Frequency": "500 Hz",
                "Duration": "10 min 0 s",
            },
            "lead_info": pd.DataFrame({"Standard": ["\U0001f7e2"] * 12}),
            "signal_quality": pd.DataFrame({"Quality Index": [0.9] * 12}),
            "annotations": {"has_annotations": True},
            "artifacts": {
                "signal_clipping": {"status": "pass"},
                "powerline_noise": {"status": "pass"},
            },
            "rpeaks": {"r_peaks": list(range(100))},
        }
        result = compute_ecg_quality_score(report)
        assert result["score"] >= 80

    def test_low_ecg_score(self):
        """Test a poor quality ECG report."""
        report = {
            "metadata": {
                "Sampling Frequency": "100 Hz",
                "Duration": "0 min 5 s",
            },
            "lead_info": pd.DataFrame({"Standard": ["\U0001f7e1"] * 2}),
            "signal_quality": pd.DataFrame({"Quality Index": [0.4, 0.3]}),
            "annotations": {"has_annotations": False},
            "artifacts": {
                "signal_clipping": {"status": "fail"},
                "powerline_noise": {"status": "fail"},
            },
            "rpeaks": {"r_peaks": [1, 2]},
        }
        result = compute_ecg_quality_score(report)
        assert result["score"] < 30

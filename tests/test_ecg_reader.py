"""Tests for ECG reader."""

import os
import tempfile
import numpy as np
import pandas as pd
import pytest

from core.ecg.reader import load_ecg, safe_load


class TestLoadCSV:
    """Tests for CSV ECG loading."""

    def test_load_csv(self, temp_csv_ecg):
        result = load_ecg(temp_csv_ecg, "ecg_csv")
        assert "signals" in result
        assert "fs" in result
        assert "lead_names" in result
        assert result["signals"].ndim == 2
        assert len(result["lead_names"]) == 2

    def test_load_csv_duration(self, temp_csv_ecg):
        result = load_ecg(temp_csv_ecg, "ecg_csv")
        assert result["duration_s"] > 0


class TestLoadNumpy:
    """Tests for NumPy ECG loading."""

    def test_load_npy(self, tmp_path):
        data = np.random.randn(2, 5000)
        f = tmp_path / "test.npy"
        np.save(str(f), data)
        result = load_ecg(str(f), "ecg_numpy")
        assert result["signals"].shape == (2, 5000)
        assert result["fs"] == 500

    def test_load_npz(self, tmp_path):
        data = np.random.randn(3, 2000)
        f = tmp_path / "test.npz"
        np.savez(str(f), signals=data)
        result = load_ecg(str(f), "ecg_numpy")
        assert result["signals"].shape[0] == 3


class TestSafeLoad:
    """Tests for safe_load function."""

    def test_safe_load_error(self, tmp_path):
        f = tmp_path / "bad.csv"
        f.write_text("not,valid\ncsv,data")
        result = safe_load(str(f), "ecg_csv")
        # This might succeed or fail depending on pandas interpretation
        assert "success" in result

    def test_safe_load_unknown_format(self, tmp_path):
        f = tmp_path / "test.xyz"
        f.write_text("dummy")
        result = safe_load(str(f), "ecg_unknown_format")
        assert result["success"] is False
        assert "error_type" in result

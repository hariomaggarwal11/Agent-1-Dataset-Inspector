"""Tests for format router."""

import os
import tempfile
import pytest

from core.format_router import route_file


class TestRouteFile:
    """Tests for route_file function."""

    def test_nonexistent_file(self):
        result = route_file("/nonexistent/file.edf")
        assert result["modality"] is None
        assert result["confidence"] == 0.0

    def test_force_eeg(self, tmp_path):
        f = tmp_path / "test.dat"
        f.write_text("dummy")
        result = route_file(str(f), force_modality="EEG")
        assert result["modality"] == "EEG"
        assert result["confidence"] == 1.0

    def test_force_ecg(self, tmp_path):
        f = tmp_path / "test.edf"
        f.write_text("dummy")
        result = route_file(str(f), force_modality="ECG")
        assert result["modality"] == "ECG"
        assert result["confidence"] == 1.0

    def test_unambiguous_eeg_set(self, tmp_path):
        f = tmp_path / "test.set"
        f.write_text("dummy")
        result = route_file(str(f))
        assert result["modality"] == "EEG"
        assert result["format"] == "eeg_eeglab"
        assert result["confidence"] >= 0.9

    def test_unambiguous_eeg_fif(self, tmp_path):
        f = tmp_path / "test.fif"
        f.write_text("dummy")
        result = route_file(str(f))
        assert result["modality"] == "EEG"
        assert result["format"] == "eeg_fif"

    def test_unambiguous_eeg_bdf(self, tmp_path):
        f = tmp_path / "test.bdf"
        f.write_text("dummy")
        result = route_file(str(f))
        assert result["modality"] == "EEG"
        assert result["format"] == "eeg_bdf"

    def test_unambiguous_ecg_dat(self, tmp_path):
        f = tmp_path / "test.dat"
        f.write_text("dummy")
        result = route_file(str(f))
        assert result["modality"] == "ECG"
        assert result["format"] == "ecg_wfdb"

    def test_unambiguous_ecg_hea(self, tmp_path):
        f = tmp_path / "test.hea"
        f.write_text("dummy")
        result = route_file(str(f))
        assert result["modality"] == "ECG"
        assert result["format"] == "ecg_wfdb"

    def test_unambiguous_ecg_csv(self, tmp_path):
        f = tmp_path / "test.csv"
        f.write_text("dummy")
        result = route_file(str(f))
        assert result["modality"] == "ECG"
        assert result["format"] == "ecg_csv"

    def test_unambiguous_ecg_npy(self, tmp_path):
        f = tmp_path / "test.npy"
        f.write_text("dummy")
        result = route_file(str(f))
        assert result["modality"] == "ECG"
        assert result["format"] == "ecg_numpy"

    def test_ambiguous_mat_defaults_eeg(self, tmp_path):
        f = tmp_path / "test.mat"
        f.write_bytes(b"MATLAB 5.0" + b"\x00" * 200)
        result = route_file(str(f))
        assert result["modality"] == "EEG"
        assert result["confidence"] <= 0.7

    def test_ambiguous_edf_with_eeg_content(self, tmp_path):
        f = tmp_path / "test.edf"
        header = b"0       " + b"EEG FP1 FP2 C3 C4" + b"\x00" * 200
        f.write_bytes(header[:256])
        result = route_file(str(f))
        assert result["modality"] == "EEG"

    def test_ambiguous_edf_with_ecg_content(self, tmp_path):
        f = tmp_path / "test.edf"
        header = b"0       " + b"ECG Lead II aVR V1" + b"\x00" * 200
        f.write_bytes(header[:256])
        result = route_file(str(f))
        assert result["modality"] == "ECG"

    def test_unknown_extension(self, tmp_path):
        f = tmp_path / "test.xyz"
        f.write_text("dummy")
        result = route_file(str(f))
        assert result["modality"] is None
        assert result["confidence"] == 0.0

    def test_dat_with_hea_companion(self, tmp_path):
        dat = tmp_path / "record.dat"
        hea = tmp_path / "record.hea"
        dat.write_text("dummy")
        hea.write_text("dummy")
        result = route_file(str(dat))
        assert result["modality"] == "ECG"

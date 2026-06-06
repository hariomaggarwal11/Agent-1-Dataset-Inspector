"""Tests for EEG reader."""

import os
import tempfile
import numpy as np
import pytest
import mne

from core.eeg.reader import load_eeg, safe_load


class TestLoadEEG:
    """Tests for load_eeg function."""

    def test_load_fif(self, sample_eeg_raw):
        """Test loading FIF format."""
        with tempfile.NamedTemporaryFile(suffix="_raw.fif", delete=False) as f:
            sample_eeg_raw.save(f.name, overwrite=True, verbose=False)
            try:
                raw = load_eeg(f.name, "eeg_fif")
                assert isinstance(raw, mne.io.BaseRaw)
                assert len(raw.info["ch_names"]) == 14
                assert raw.info["sfreq"] == 128
            finally:
                os.unlink(f.name)

    def test_load_unknown_format_raises(self):
        """Test that unknown format raises ValueError."""
        with pytest.raises(ValueError, match="Unknown EEG format key"):
            load_eeg("/tmp/fake.xyz", "eeg_unknown_format")


class TestSafeLoad:
    """Tests for safe_load function."""

    def test_safe_load_returns_error_on_bad_file(self, tmp_path):
        """Test that safe_load handles errors gracefully."""
        f = tmp_path / "corrupt.fif"
        f.write_bytes(b"not a real fif file")
        result = safe_load(str(f), "eeg_fif")
        assert result["success"] is False
        assert "error_type" in result
        assert "message" in result
        assert "suggestion" in result

    def test_safe_load_success(self, sample_eeg_raw):
        """Test that safe_load returns data on success."""
        with tempfile.NamedTemporaryFile(suffix="_raw.fif", delete=False) as f:
            sample_eeg_raw.save(f.name, overwrite=True, verbose=False)
            try:
                result = safe_load(f.name, "eeg_fif")
                assert result["success"] is True
                assert isinstance(result["data"], mne.io.BaseRaw)
            finally:
                os.unlink(f.name)

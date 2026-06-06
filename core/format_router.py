"""Format router for NeuroInspect - identifies file modality and format."""

import os

from config import EEG_EXTENSIONS, ECG_EXTENSIONS


# Internal format key mapping (extension -> format_key)
_EEG_FORMAT_MAP = {
    ".edf": "eeg_edf",
    ".bdf": "eeg_bdf",
    ".gdf": "eeg_gdf",
    ".set": "eeg_eeglab",
    ".fdt": "eeg_eeglab",
    ".fif": "eeg_fif",
    ".vhdr": "eeg_brainvision",
    ".vmrk": "eeg_brainvision",
    ".eeg": "eeg_brainvision",
    ".cnt": "eeg_cnt",
    ".mff": "eeg_mff",
    ".mat": "eeg_mat",
    ".h5": "eeg_hdf5",
    ".hdf5": "eeg_hdf5",
    ".xdf": "eeg_xdf",
}

_ECG_FORMAT_MAP = {
    ".dat": "ecg_wfdb",
    ".hea": "ecg_wfdb",
    ".atr": "ecg_wfdb",
    ".qrs": "ecg_wfdb",
    ".csv": "ecg_csv",
    ".edf": "ecg_edf",
    ".mat": "ecg_mat",
    ".h5": "ecg_hdf5",
    ".hdf5": "ecg_hdf5",
    ".xml": "ecg_xml",
    ".dcm": "ecg_dicom",
    ".npy": "ecg_numpy",
    ".npz": "ecg_numpy",
    ".json": "ecg_json",
}

# Extensions that are ambiguous between EEG and ECG
_AMBIGUOUS_EXTENSIONS = {".edf", ".mat", ".h5", ".hdf5"}


def _check_magic_bytes(filepath):
    """Inspect file magic bytes to help disambiguate format.

    Returns a hint string: 'eeg', 'ecg', or 'unknown'.
    """
    try:
        with open(filepath, "rb") as f:
            header = f.read(256)

        # EDF/BDF: starts with '0' (EDF) or 0xff (BDF)
        if header[:8] == b"0       ":
            header_str = header.decode("ascii", errors="ignore").upper()
            ecg_indicators = ["ECG", "EKG", "LEAD", "II", "V1", "AVR", "AVL", "AVF"]
            eeg_indicators = ["EEG", "FP1", "FP2", "C3", "C4", "O1", "O2", "CZ", "PZ"]
            ecg_score = sum(1 for ind in ecg_indicators if ind in header_str)
            eeg_score = sum(1 for ind in eeg_indicators if ind in header_str)
            if ecg_score > eeg_score:
                return "ecg"
            elif eeg_score > ecg_score:
                return "eeg"
            return "unknown"

        # HDF5 magic bytes
        if header[:8] == b"\x89HDF\r\n\x1a\n":
            return "unknown"

        # MATLAB v5 magic bytes
        if header[:4] == b"MATL" or (len(header) >= 128 and header[124:128] == b"\x00\x01IM"):
            return "unknown"

        # Check for companion .hea file (WFDB indicator)
        base = os.path.splitext(filepath)[0]
        if os.path.exists(base + ".hea"):
            return "ecg"

    except (OSError, IOError):
        pass

    return "unknown"


def route_file(filepath, force_modality="auto"):
    """Route a signal file to the appropriate reader.

    Parameters
    ----------
    filepath : str
        Path to the signal file.
    force_modality : str
        One of 'auto', 'EEG', 'ECG'. If not 'auto', forces the modality.

    Returns
    -------
    dict
        Keys: modality, format, reader_fn, confidence, note
    """
    if not os.path.exists(filepath):
        return {
            "modality": None,
            "format": None,
            "reader_fn": None,
            "confidence": 0.0,
            "note": f"File not found: {filepath}",
        }

    ext = os.path.splitext(filepath)[1].lower()

    # Handle forced modality
    if force_modality.upper() == "EEG":
        fmt = _EEG_FORMAT_MAP.get(ext, "eeg_unknown")
        return {
            "modality": "EEG",
            "format": fmt,
            "reader_fn": "load_eeg",
            "confidence": 1.0,
            "note": "Modality forced to EEG by user.",
        }
    elif force_modality.upper() == "ECG":
        fmt = _ECG_FORMAT_MAP.get(ext, "ecg_unknown")
        return {
            "modality": "ECG",
            "format": fmt,
            "reader_fn": "load_ecg",
            "confidence": 1.0,
            "note": "Modality forced to ECG by user.",
        }

    # Auto-detect: check extension first
    is_eeg_only = ext in EEG_EXTENSIONS and ext not in ECG_EXTENSIONS
    is_ecg_only = ext in ECG_EXTENSIONS and ext not in EEG_EXTENSIONS

    if is_eeg_only:
        fmt = _EEG_FORMAT_MAP.get(ext, "eeg_unknown")
        return {
            "modality": "EEG",
            "format": fmt,
            "reader_fn": "load_eeg",
            "confidence": 0.9,
            "note": f"Identified as EEG by extension ({ext}).",
        }
    elif is_ecg_only:
        fmt = _ECG_FORMAT_MAP.get(ext, "ecg_unknown")
        return {
            "modality": "ECG",
            "format": fmt,
            "reader_fn": "load_ecg",
            "confidence": 0.9,
            "note": f"Identified as ECG by extension ({ext}).",
        }

    # Ambiguous - inspect file contents
    if ext in _AMBIGUOUS_EXTENSIONS:
        hint = _check_magic_bytes(filepath)
        if hint == "eeg":
            fmt = _EEG_FORMAT_MAP.get(ext, "eeg_unknown")
            return {
                "modality": "EEG",
                "format": fmt,
                "reader_fn": "load_eeg",
                "confidence": 0.7,
                "note": f"Ambiguous extension ({ext}), content analysis suggests EEG.",
            }
        elif hint == "ecg":
            fmt = _ECG_FORMAT_MAP.get(ext, "ecg_unknown")
            return {
                "modality": "ECG",
                "format": fmt,
                "reader_fn": "load_ecg",
                "confidence": 0.7,
                "note": f"Ambiguous extension ({ext}), content analysis suggests ECG.",
            }
        else:
            # Default ambiguous to EEG with low confidence warning
            fmt = _EEG_FORMAT_MAP.get(ext, "eeg_unknown")
            return {
                "modality": "EEG",
                "format": fmt,
                "reader_fn": "load_eeg",
                "confidence": 0.5,
                "note": (f"Ambiguous extension ({ext}), defaulting to EEG. "
                         "Use force_modality to override if this is an ECG file."),
            }

    # Unknown extension
    return {
        "modality": None,
        "format": None,
        "reader_fn": None,
        "confidence": 0.0,
        "note": f"Unrecognized file extension: {ext}",
    }

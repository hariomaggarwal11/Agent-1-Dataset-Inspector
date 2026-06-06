"""ECG file reader using WFDB and NeuroKit2."""

import os
import numpy as np
import pandas as pd


def load_ecg(filepath, format_key):
    """Load ECG file into standardized dict.

    Parameters
    ----------
    filepath : str
        Path to the ECG file.
    format_key : str
        Format identifier from the router.

    Returns
    -------
    dict
        Standardized ECG data dict with keys:
        signals, fs, lead_names, units, gain, baseline, duration_s,
        record_info, annotations.
    """
    loaders = {
        "ecg_wfdb": _load_wfdb,
        "ecg_csv": _load_csv_ecg,
        "ecg_numpy": _load_numpy_ecg,
        "ecg_mat": _load_mat_ecg,
        "ecg_hdf5": _load_hdf5_ecg,
        "ecg_edf": _load_edf_ecg,
        "ecg_json": _load_json_ecg,
    }

    loader = loaders.get(format_key)
    if loader is None:
        raise ValueError(f"Unknown ECG format key: {format_key}")

    return loader(filepath)


def _load_wfdb(filepath):
    """Read PhysioNet WFDB format."""
    import wfdb

    # Strip extensions to get record name
    record_name = filepath
    for ext in [".hea", ".dat", ".atr", ".qrs"]:
        record_name = record_name.replace(ext, "")

    record = wfdb.rdrecord(record_name)

    # Try to load annotation file
    ann = None
    for ext in ["atr", "qrs", "ari", "ecg"]:
        try:
            ann = wfdb.rdann(record_name, ext)
            break
        except (FileNotFoundError, Exception):
            continue

    return {
        "signals": record.p_signal.T,  # (n_leads, n_samples)
        "fs": record.fs,
        "lead_names": record.sig_name,
        "units": record.units,
        "gain": list(record.adc_gain) if record.adc_gain is not None else [],
        "baseline": list(record.baseline) if record.baseline is not None else [],
        "duration_s": record.sig_len / record.fs,
        "record_info": {
            "comments": record.comments if record.comments else [],
            "record_name": record.record_name,
        },
        "annotations": ann,
    }


def _load_csv_ecg(filepath):
    """Load ECG from CSV file."""
    df = pd.read_csv(filepath)

    # Try to detect columns
    # Assume first column might be time, rest are leads
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    if len(numeric_cols) == 0:
        raise ValueError("No numeric columns found in CSV file")

    # Check if first column looks like time (monotonically increasing)
    first_col = df[numeric_cols[0]].values
    if len(first_col) > 1 and np.all(np.diff(first_col) > 0):
        # First column is likely time
        time_col = numeric_cols[0]
        data_cols = numeric_cols[1:]
        # Infer sampling rate from time column
        dt = np.median(np.diff(first_col))
        fs = int(round(1.0 / dt)) if dt > 0 else 500
    else:
        data_cols = numeric_cols
        fs = 500  # default

    signals = df[data_cols].values.T  # (n_leads, n_samples)
    lead_names = list(data_cols)

    return {
        "signals": signals,
        "fs": fs,
        "lead_names": lead_names,
        "units": ["mV"] * len(lead_names),
        "gain": [1.0] * len(lead_names),
        "baseline": [0.0] * len(lead_names),
        "duration_s": signals.shape[1] / fs,
        "record_info": {"comments": [], "record_name": os.path.basename(filepath)},
        "annotations": None,
    }


def _load_numpy_ecg(filepath):
    """Load ECG from NumPy .npy or .npz file."""
    if filepath.endswith(".npz"):
        npz = np.load(filepath)
        # Look for signal data
        keys = list(npz.keys())
        data = npz[keys[0]]
    else:
        data = np.load(filepath)

    if data.ndim == 1:
        data = data.reshape(1, -1)
    elif data.shape[0] > data.shape[1]:
        data = data.T

    n_leads = data.shape[0]
    fs = 500  # default

    return {
        "signals": data,
        "fs": fs,
        "lead_names": [f"Lead{i+1}" for i in range(n_leads)],
        "units": ["mV"] * n_leads,
        "gain": [1.0] * n_leads,
        "baseline": [0.0] * n_leads,
        "duration_s": data.shape[1] / fs,
        "record_info": {"comments": [], "record_name": os.path.basename(filepath)},
        "annotations": None,
    }


def _load_mat_ecg(filepath):
    """Load ECG from MATLAB .mat file."""
    try:
        from scipy.io import loadmat
        mat = loadmat(filepath, squeeze_me=True)
    except Exception:
        from pymatreader import read_mat
        mat = read_mat(filepath)

    # Find the largest numeric array
    data = None
    for key in mat:
        if key.startswith("_"):
            continue
        val = mat[key]
        if isinstance(val, np.ndarray) and val.ndim >= 1:
            if val.dtype in [np.float32, np.float64, np.int16, np.int32]:
                if data is None or val.size > data.size:
                    data = val

    if data is None:
        raise ValueError("No ECG data found in .mat file")

    if data.ndim == 1:
        data = data.reshape(1, -1)
    elif data.shape[0] > data.shape[1]:
        data = data.T

    n_leads = data.shape[0]
    fs = 500  # default

    # Try to find fs in mat
    for key in ["fs", "Fs", "sfreq", "sampling_rate"]:
        if key in mat and np.isscalar(mat[key]):
            fs = int(mat[key])
            break

    return {
        "signals": data,
        "fs": fs,
        "lead_names": [f"Lead{i+1}" for i in range(n_leads)],
        "units": ["mV"] * n_leads,
        "gain": [1.0] * n_leads,
        "baseline": [0.0] * n_leads,
        "duration_s": data.shape[1] / fs,
        "record_info": {"comments": [], "record_name": os.path.basename(filepath)},
        "annotations": None,
    }


def _load_hdf5_ecg(filepath):
    """Load ECG from HDF5 file."""
    import h5py

    with h5py.File(filepath, "r") as f:
        data = None
        for key in ["data", "ecg", "ECG", "signals", "raw"]:
            if key in f:
                data = np.array(f[key])
                break

        if data is None:
            for key in f.keys():
                if isinstance(f[key], h5py.Dataset):
                    data = np.array(f[key])
                    break

        if data is None:
            raise ValueError("No data found in HDF5 file")

        fs = 500
        for attr_key in ["fs", "sfreq", "sampling_rate"]:
            if attr_key in f.attrs:
                fs = int(f.attrs[attr_key])
                break

    if data.ndim == 1:
        data = data.reshape(1, -1)
    elif data.shape[0] > data.shape[1]:
        data = data.T

    n_leads = data.shape[0]

    return {
        "signals": data,
        "fs": fs,
        "lead_names": [f"Lead{i+1}" for i in range(n_leads)],
        "units": ["mV"] * n_leads,
        "gain": [1.0] * n_leads,
        "baseline": [0.0] * n_leads,
        "duration_s": data.shape[1] / fs,
        "record_info": {"comments": [], "record_name": os.path.basename(filepath)},
        "annotations": None,
    }


def _load_edf_ecg(filepath):
    """Load ECG from EDF file using MNE."""
    import mne

    raw = mne.io.read_raw_edf(filepath, preload=True, verbose=False)
    data = raw.get_data()
    fs = int(raw.info["sfreq"])

    return {
        "signals": data,
        "fs": fs,
        "lead_names": raw.info["ch_names"],
        "units": ["mV"] * len(raw.info["ch_names"]),
        "gain": [1.0] * len(raw.info["ch_names"]),
        "baseline": [0.0] * len(raw.info["ch_names"]),
        "duration_s": data.shape[1] / fs,
        "record_info": {"comments": [], "record_name": os.path.basename(filepath)},
        "annotations": None,
    }


def _load_json_ecg(filepath):
    """Load ECG from JSON file."""
    import json

    with open(filepath, "r") as f:
        content = json.load(f)

    # Expect structure: {signals: [...], fs: int, ...}
    if isinstance(content, dict):
        if "signals" in content:
            data = np.array(content["signals"])
        elif "data" in content:
            data = np.array(content["data"])
        else:
            raise ValueError("JSON must contain 'signals' or 'data' key")

        fs = content.get("fs", content.get("sampling_rate", 500))
    else:
        data = np.array(content)
        fs = 500

    if data.ndim == 1:
        data = data.reshape(1, -1)
    elif data.shape[0] > data.shape[1]:
        data = data.T

    n_leads = data.shape[0]

    return {
        "signals": data,
        "fs": fs,
        "lead_names": [f"Lead{i+1}" for i in range(n_leads)],
        "units": ["mV"] * n_leads,
        "gain": [1.0] * n_leads,
        "baseline": [0.0] * n_leads,
        "duration_s": data.shape[1] / fs,
        "record_info": {"comments": [], "record_name": os.path.basename(filepath)},
        "annotations": None,
    }


def safe_load(filepath, format_key):
    """Safely load an ECG file with error handling.

    Returns
    -------
    dict
        Keys: success (bool), data or error_type/message/suggestion.
    """
    from config import ERROR_SUGGESTIONS

    try:
        ecg_data = load_ecg(filepath, format_key)
        return {"success": True, "data": ecg_data}
    except Exception as e:
        error_type = type(e).__name__
        suggestion = ERROR_SUGGESTIONS.get(
            error_type,
            "An unexpected error occurred. Please check the file format."
        )
        return {
            "success": False,
            "error_type": error_type,
            "message": str(e),
            "suggestion": suggestion,
        }

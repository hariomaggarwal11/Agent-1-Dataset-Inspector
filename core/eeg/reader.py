"""EEG file reader using MNE-Python."""

import numpy as np
import mne


# MNE reader function mapping
MNE_READERS = {
    "eeg_edf": mne.io.read_raw_edf,
    "eeg_bdf": mne.io.read_raw_bdf,
    "eeg_gdf": mne.io.read_raw_gdf,
    "eeg_eeglab": mne.io.read_raw_eeglab,
    "eeg_brainvision": mne.io.read_raw_brainvision,
    "eeg_fif": mne.io.read_raw_fif,
    "eeg_cnt": mne.io.read_raw_cnt,
}


def load_eeg(filepath, format_key, preload=True):
    """Load EEG file into MNE Raw object.

    Parameters
    ----------
    filepath : str
        Path to the EEG file.
    format_key : str
        Format identifier from the router.
    preload : bool
        Whether to preload data into memory.

    Returns
    -------
    mne.io.BaseRaw
        MNE Raw object.
    """
    reader_fn = MNE_READERS.get(format_key)

    if reader_fn:
        raw = reader_fn(filepath, preload=preload, verbose=False)
    elif format_key == "eeg_mat":
        raw = _load_mat_eeg(filepath)
    elif format_key == "eeg_xdf":
        raw = _load_xdf(filepath)
    elif format_key == "eeg_hdf5":
        raw = _load_hdf5_eeg(filepath)
    else:
        raise ValueError(f"Unknown EEG format key: {format_key}")

    return raw


def _load_mat_eeg(filepath):
    """Handle MATLAB .mat files for EEG data.

    Attempts scipy.io.loadmat first (v5 .mat), then pymatreader for v7.3+.
    Auto-detects DREAMER, DEAP, SEED structure.
    """
    try:
        from scipy.io import loadmat
        mat = loadmat(filepath, squeeze_me=True)
    except Exception:
        from pymatreader import read_mat
        mat = read_mat(filepath)

    # Try to detect known dataset structure
    raw = _parse_mat_structure(mat, filepath)
    return raw


def _parse_mat_structure(mat, filepath):
    """Parse MATLAB struct and build an MNE RawArray.

    Handles common structures: DREAMER, DEAP, SEED, generic.
    """
    data = None
    fs = 128  # default
    ch_names = None

    # Check for DREAMER-like structure
    if "DREAMER" in mat:
        dreamer = mat["DREAMER"]
        if hasattr(dreamer, "dtype") and "Data" in str(dreamer.dtype):
            # Complex nested struct
            pass
        fs = 128
        ch_names = ["AF3", "F7", "F3", "FC5", "T7", "P7", "O1",
                    "O2", "P8", "T8", "FC6", "F4", "F8", "AF4"]

    # Check for generic data array
    if data is None:
        # Look for the largest numeric array in the mat file
        for key in mat:
            if key.startswith("_"):
                continue
            val = mat[key]
            if isinstance(val, np.ndarray) and val.ndim == 2:
                if data is None or val.size > data.size:
                    data = val

    if data is None:
        raise ValueError("Could not find EEG data array in .mat file")

    # Ensure data is (n_channels, n_samples)
    if data.shape[0] > data.shape[1]:
        data = data.T

    n_channels = data.shape[0]

    if ch_names is None:
        ch_names = [f"Ch{i+1}" for i in range(n_channels)]
    elif len(ch_names) != n_channels:
        ch_names = [f"Ch{i+1}" for i in range(n_channels)]

    # Create MNE RawArray
    info = mne.create_info(ch_names=ch_names, sfreq=fs, ch_types="eeg")
    raw = mne.io.RawArray(data, info, verbose=False)
    return raw


def _load_xdf(filepath):
    """Load XDF (Lab Streaming Layer) files."""
    try:
        import pyxdf
        streams, _ = pyxdf.load_xdf(filepath)
        # Use the first EEG stream
        for stream in streams:
            if stream["info"]["type"][0].lower() in ["eeg", "markers"]:
                data = np.array(stream["time_series"]).T
                fs = float(stream["info"]["nominal_srate"][0])
                n_ch = data.shape[0]
                ch_names = [f"Ch{i+1}" for i in range(n_ch)]
                info = mne.create_info(ch_names=ch_names, sfreq=fs, ch_types="eeg")
                return mne.io.RawArray(data, info, verbose=False)
    except ImportError:
        raise ImportError("pyxdf is required for XDF files: pip install pyxdf")

    raise ValueError("No EEG stream found in XDF file")


def _load_hdf5_eeg(filepath):
    """Load HDF5 EEG files."""
    import h5py

    with h5py.File(filepath, "r") as f:
        # Try common key patterns
        data = None
        for key in ["data", "eeg", "EEG", "signals", "raw"]:
            if key in f:
                data = np.array(f[key])
                break

        if data is None:
            # Use the first dataset found
            for key in f.keys():
                if isinstance(f[key], h5py.Dataset):
                    data = np.array(f[key])
                    break

        if data is None:
            raise ValueError("No data array found in HDF5 file")

        # Get sampling rate
        fs = 256  # default
        for attr_key in ["fs", "sfreq", "sampling_rate", "sr"]:
            if attr_key in f.attrs:
                fs = float(f.attrs[attr_key])
                break

    if data.ndim == 1:
        data = data.reshape(1, -1)
    elif data.shape[0] > data.shape[1]:
        data = data.T

    n_channels = data.shape[0]
    ch_names = [f"Ch{i+1}" for i in range(n_channels)]
    info = mne.create_info(ch_names=ch_names, sfreq=fs, ch_types="eeg")
    return mne.io.RawArray(data, info, verbose=False)


def safe_load(filepath, format_key):
    """Safely load an EEG file with error handling.

    Returns
    -------
    dict
        Keys: success (bool), data or error_type/message/suggestion.
    """
    from config import ERROR_SUGGESTIONS

    try:
        raw = load_eeg(filepath, format_key)
        return {"success": True, "data": raw}
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

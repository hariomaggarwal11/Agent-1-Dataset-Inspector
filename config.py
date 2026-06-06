"""NeuroInspect configuration constants."""

# EEG frequency bands (Hz)
EEG_BANDS = {
    "Delta": (0.5, 4.0),
    "Theta": (4.0, 8.0),
    "Alpha": (8.0, 13.0),
    "Beta": (13.0, 30.0),
    "Gamma": (30.0, 45.0),
}

# Dark theme color constants
THEME_COLORS = {
    "--bg-primary": "#0a0e1a",
    "--bg-surface": "#111827",
    "--bg-elevated": "#1a2235",
    "--accent-eeg": "#00d4ff",
    "--accent-ecg": "#ff4d6d",
    "--accent-ok": "#22c55e",
    "--accent-warn": "#f59e0b",
    "--accent-fail": "#ef4444",
    "--text-primary": "#f1f5f9",
    "--text-muted": "#64748b",
    "--border": "#1e2d45",
}

# Known EEG datasets for auto-recognition
KNOWN_EEG_DATASETS = {
    "DREAMER": {
        "description": "Database for Emotion Recognition through EEG and ECG Signals",
        "format": ".mat",
        "channels": 14,
        "channel_names": ["AF3", "F7", "F3", "FC5", "T7", "P7", "O1",
                          "O2", "P8", "T8", "FC6", "F4", "F8", "AF4"],
        "fs": 128,
        "device": "Emotiv EPOC (14-channel)",
        "labels": {
            "arousal": {1: "Low", 2: "Med-Low", 3: "Med", 4: "Med-High", 5: "High"},
            "valence": {1: "Low", 2: "Med-Low", 3: "Med", 4: "Med-High", 5: "High"},
            "dominance": {1: "Low", 2: "Med-Low", 3: "Med", 4: "Med-High", 5: "High"},
        },
        "preprocessing": "Bandpass 4-45 Hz, ICA artifact removal",
    },
    "DEAP": {
        "description": "Dataset for Emotion Analysis using Physiological signals",
        "format": ".bdf",
        "channels": 32,
        "fs": 512,
        "device": "BioSemi ActiveTwo (32-channel)",
        "labels": {
            "arousal": {1: "Low", 9: "High"},
            "valence": {1: "Low", 9: "High"},
            "dominance": {1: "Low", 9: "High"},
            "liking": {1: "Low", 9: "High"},
        },
        "preprocessing": "Bandpass 4-45 Hz, EOG removal, downsampling to 128 Hz",
    },
    "SEED": {
        "description": "SJTU Emotion EEG Dataset",
        "format": ".mat",
        "channels": 62,
        "fs": 200,
        "device": "ESI NeuroScan (62-channel)",
        "labels": {
            "emotion": {-1: "Negative", 0: "Neutral", 1: "Positive"},
        },
        "preprocessing": "Bandpass 0.3-50 Hz",
    },
    "MAHNOB-HCI": {
        "description": "Multimodal Database for Affect Recognition and Implicit Tagging",
        "format": ".bdf",
        "channels": 32,
        "fs": 256,
        "device": "BioSemi ActiveTwo (32-channel)",
        "labels": {
            "arousal": {1: "Low", 9: "High"},
            "valence": {1: "Low", 9: "High"},
        },
        "preprocessing": "Bandpass 4-45 Hz",
    },
    "PhysioNet Motor Imagery": {
        "description": "EEG Motor Movement/Imagery Dataset",
        "format": ".edf",
        "channels": 64,
        "fs": 160,
        "device": "BCI2000 (64-channel)",
        "labels": {
            "task": {
                "T0": "Rest",
                "T1": "Left fist",
                "T2": "Right fist",
                "T3": "Both fists",
                "T4": "Both feet",
            },
        },
        "preprocessing": "Bandpass 8-30 Hz for motor imagery",
    },
    "BCICIV": {
        "description": "BCI Competition IV Dataset 2a/2b",
        "format": ".gdf",
        "channels": 22,
        "fs": 250,
        "device": "22 Ag/AgCl electrodes",
        "labels": {
            "class": {1: "Left hand", 2: "Right hand", 3: "Both feet", 4: "Tongue"},
        },
        "preprocessing": "Bandpass 4-40 Hz, CAR",
    },
}

# Known ECG datasets for auto-recognition
KNOWN_ECG_DATASETS = {
    "MIT-BIH Arrhythmia": {
        "description": "MIT-BIH Arrhythmia Database",
        "format": ".dat",
        "leads": ["MLII", "V1"],
        "fs": 360,
        "n_leads": 2,
        "label_map": {
            "N": "Normal beat",
            "L": "Left bundle branch block",
            "R": "Right bundle branch block",
            "V": "Premature ventricular contraction",
            "A": "Atrial premature beat",
            "F": "Fusion of ventricular and normal",
            "/": "Paced beat",
            "Q": "Unclassifiable beat",
        },
    },
    "PTB Diagnostic": {
        "description": "PTB Diagnostic ECG Database",
        "format": ".dat",
        "leads": ["I", "II", "III", "aVR", "aVL", "aVF",
                  "V1", "V2", "V3", "V4", "V5", "V6",
                  "VX", "VY", "VZ"],
        "fs": 1000,
        "n_leads": 15,
        "label_map": {
            "Myocardial infarction": "MI",
            "Healthy control": "Normal",
        },
    },
    "PTB-XL": {
        "description": "PTB-XL Electrocardiography Database",
        "format": ".dat",
        "leads": ["I", "II", "III", "aVR", "aVL", "aVF",
                  "V1", "V2", "V3", "V4", "V5", "V6"],
        "fs": 500,
        "n_leads": 12,
        "label_map": {
            "NORM": "Normal ECG",
            "MI": "Myocardial Infarction",
            "STTC": "ST/T Change",
            "CD": "Conduction Disturbance",
            "HYP": "Hypertrophy",
        },
    },
    "CPSC2018": {
        "description": "China Physiological Signal Challenge 2018",
        "format": ".mat",
        "leads": ["I", "II", "III", "aVR", "aVL", "aVF",
                  "V1", "V2", "V3", "V4", "V5", "V6"],
        "fs": 500,
        "n_leads": 12,
        "label_map": {
            "AF": "Atrial Fibrillation",
            "I-AVB": "First-degree AV Block",
            "LBBB": "Left Bundle Branch Block",
            "RBBB": "Right Bundle Branch Block",
            "PAC": "Premature Atrial Contraction",
            "PVC": "Premature Ventricular Contraction",
            "STD": "ST Depression",
            "STE": "ST Elevation",
            "Normal": "Normal",
        },
    },
    "PhysioNet Challenge": {
        "description": "PhysioNet/Computing in Cardiology Challenge 2020/2021",
        "format": ".dat",
        "leads": ["I", "II", "III", "aVR", "aVL", "aVF",
                  "V1", "V2", "V3", "V4", "V5", "V6"],
        "fs": 500,
        "n_leads": 12,
        "label_map": {},
    },
}

# Supported EEG file extensions
EEG_EXTENSIONS = {
    ".edf": "European Data Format",
    ".bdf": "BioSemi Data Format",
    ".gdf": "General Data Format",
    ".set": "EEGLAB Dataset",
    ".fdt": "EEGLAB Data (companion)",
    ".fif": "MNE-Python FIF Format",
    ".vhdr": "BrainVision Header",
    ".vmrk": "BrainVision Markers",
    ".eeg": "BrainVision EEG",
    ".cnt": "Neuroscan CNT",
    ".mff": "EGI MFF Format",
    ".mat": "MATLAB Format",
    ".h5": "HDF5 Format",
    ".hdf5": "HDF5 Format",
    ".xdf": "XDF (LSL recordings)",
}

# Supported ECG file extensions
ECG_EXTENSIONS = {
    ".dat": "PhysioNet WFDB Format",
    ".hea": "WFDB Header",
    ".atr": "WFDB Annotation",
    ".qrs": "WFDB QRS Annotation",
    ".csv": "CSV Format",
    ".edf": "European Data Format",
    ".mat": "MATLAB Format",
    ".h5": "HDF5 Format",
    ".hdf5": "HDF5 Format",
    ".xml": "XML ECG Format",
    ".dcm": "DICOM ECG",
    ".npy": "NumPy Array",
    ".npz": "NumPy Compressed",
    ".json": "JSON Format",
}

# Standard 12-lead ECG names
STANDARD_LEAD_NAMES = {
    "I", "II", "III",
    "aVR", "aVL", "aVF",
    "V1", "V2", "V3", "V4", "V5", "V6",
}

# Holter lead names
HOLTER_LEADS = {"MLII", "V5", "V1"}

# Common error suggestions
ERROR_SUGGESTIONS = {
    "FileNotFoundError": "Ensure the companion file (e.g., .hea for .dat) is in the same directory.",
    "ValueError": "The file may be corrupted or in an unexpected internal format.",
    "MemoryError": "The file is very large. Switch to 'Quick Scan' mode.",
    "KeyError": "MATLAB struct keys not recognized. Specify the dataset manually.",
    "EOFError": "The file appears to be truncated or incomplete.",
    "PermissionError": "Ensure you have read permissions for the file.",
    "ImportError": "A required package is missing. Run: pip install -r requirements.txt",
    "UnicodeDecodeError": "The file contains unexpected encoding. Ensure it is a valid signal file.",
}

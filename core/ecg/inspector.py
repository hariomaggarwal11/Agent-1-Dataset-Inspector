"""ECG Inspector - R-peaks, HRV, annotations, signal quality."""

import numpy as np
import pandas as pd

from config import KNOWN_ECG_DATASETS, STANDARD_LEAD_NAMES, HOLTER_LEADS


def extract_lead_info(ecg_data):
    """Extract per-lead metadata table.

    Returns
    -------
    pd.DataFrame
        Lead information table.
    """
    rows = []
    lead_names = ecg_data["lead_names"]
    units = ecg_data.get("units", ["mV"] * len(lead_names))
    gain = ecg_data.get("gain", [1.0] * len(lead_names))
    baseline = ecg_data.get("baseline", [0.0] * len(lead_names))

    for idx, name in enumerate(lead_names):
        is_standard = name in STANDARD_LEAD_NAMES or name in HOLTER_LEADS
        rows.append({
            "Index": idx,
            "Lead Name": name,
            "Unit": units[idx] if idx < len(units) else "mV",
            "Gain (mV/adu)": gain[idx] if idx < len(gain) else 1.0,
            "Baseline": baseline[idx] if idx < len(baseline) else 0.0,
            "Standard": "\U0001f7e2" if is_standard else "\U0001f7e1 Non-standard",
        })

    return pd.DataFrame(rows)


def extract_annotations(ecg_data):
    """Extract annotation information from ECG data.

    Returns
    -------
    dict
        Keys: has_annotations, annotation_df, beat_summary
    """
    ann = ecg_data.get("annotations")
    if ann is None:
        return {"has_annotations": False, "annotation_df": None, "beat_summary": None}

    fs = ecg_data["fs"]

    # Build annotation table
    beat_symbols = {
        "N": "Normal beat",
        "L": "Left bundle branch block",
        "R": "Right bundle branch block",
        "V": "Premature ventricular contraction (PVC)",
        "A": "Atrial premature beat (PAC)",
        "F": "Fusion of ventricular and normal",
        "/": "Paced beat",
        "f": "Fusion of paced and normal",
        "Q": "Unclassifiable beat",
        "+": "Rhythm change",
        "~": "Signal quality change",
        "|": "Isolated QRS-like artifact",
    }

    rows = []
    for i in range(min(len(ann.sample), 1000)):  # Limit to 1000 for display
        sample = ann.sample[i]
        symbol = ann.symbol[i]
        aux = ann.aux_note[i] if hasattr(ann, "aux_note") and i < len(ann.aux_note) else ""
        rows.append({
            "Time (s)": round(sample / fs, 3),
            "Sample": sample,
            "Symbol": symbol,
            "Meaning": beat_symbols.get(symbol, "Unknown"),
            "Note": aux if aux else "\u2014",
        })

    annotation_df = pd.DataFrame(rows)

    # Beat count summary
    all_symbols = list(ann.symbol)
    unique_symbols = set(all_symbols)
    total = len(all_symbols)

    summary_rows = []
    for sym in sorted(unique_symbols):
        count = all_symbols.count(sym)
        pct = (count / total * 100) if total > 0 else 0
        meaning = beat_symbols.get(sym, "Unknown")

        if sym == "N":
            status = "\U0001f7e2"
        elif sym in ("V", "A", "F"):
            status = "\U0001f7e1"
        elif sym == "Q":
            status = "\U0001f534"
        else:
            status = "\u26aa"

        summary_rows.append({
            "Symbol": sym,
            "Meaning": meaning,
            "Count": count,
            "Percentage": f"{pct:.1f}%",
            "Status": status,
        })

    beat_summary = pd.DataFrame(summary_rows)
    beat_summary = beat_summary.sort_values("Count", ascending=False).reset_index(drop=True)

    return {
        "has_annotations": True,
        "annotation_df": annotation_df,
        "beat_summary": beat_summary,
        "total_annotations": total,
    }


def compute_rpeaks(ecg_data, lead_idx=None):
    """Compute R-peaks and heart rate statistics.

    Parameters
    ----------
    ecg_data : dict
        Standardized ECG data dict.
    lead_idx : int or None
        Index of lead to analyze. If None, uses lead II or first available.

    Returns
    -------
    dict
        Keys: r_peaks, rr_intervals, hr_stats, hrv_metrics
    """
    import neurokit2 as nk

    signals = ecg_data["signals"]
    fs = ecg_data["fs"]
    lead_names = ecg_data["lead_names"]

    # Select best lead for R-peak detection
    if lead_idx is None:
        # Prefer lead II, then MLII, then first lead
        for preferred in ["II", "MLII", "Lead II"]:
            if preferred in lead_names:
                lead_idx = lead_names.index(preferred)
                break
        if lead_idx is None:
            lead_idx = 0

    signal = signals[lead_idx]

    # R-peak detection using NeuroKit2
    try:
        _, info = nk.ecg_peaks(signal, sampling_rate=fs)
        r_peaks = info["ECG_R_Peaks"]
    except Exception:
        # Fallback: simple threshold-based detection
        r_peaks = _simple_rpeak_detection(signal, fs)

    if len(r_peaks) < 2:
        return {
            "r_peaks": r_peaks,
            "rr_intervals": np.array([]),
            "hr_stats": {"mean_hr": 0, "classification": "Insufficient data"},
            "hrv_metrics": {},
            "lead_used": lead_names[lead_idx],
        }

    # RR intervals in ms
    rr_intervals = np.diff(r_peaks) / fs * 1000

    # Heart rate (BPM)
    hr = 60000.0 / rr_intervals
    mean_hr = np.mean(hr)
    std_hr = np.std(hr)

    # Classification
    if mean_hr < 60:
        hr_class = "Bradycardia"
    elif mean_hr > 100:
        hr_class = "Tachycardia"
    else:
        hr_class = "Normal Sinus Rhythm"

    # HRV metrics
    sdnn = np.std(rr_intervals, ddof=1)
    rmssd = np.sqrt(np.mean(np.diff(rr_intervals) ** 2))
    nn50 = np.sum(np.abs(np.diff(rr_intervals)) > 50)
    pnn50 = (nn50 / len(rr_intervals)) * 100 if len(rr_intervals) > 0 else 0

    return {
        "r_peaks": r_peaks,
        "rr_intervals": rr_intervals,
        "hr_stats": {
            "mean_hr": round(mean_hr, 1),
            "std_hr": round(std_hr, 1),
            "min_hr": round(np.min(hr), 1),
            "max_hr": round(np.max(hr), 1),
            "classification": hr_class,
        },
        "hrv_metrics": {
            "SDNN (ms)": round(sdnn, 1),
            "RMSSD (ms)": round(rmssd, 1),
            "pNN50 (%)": round(pnn50, 1),
            "Mean RR (ms)": round(np.mean(rr_intervals), 1),
        },
        "lead_used": lead_names[lead_idx],
    }


def _simple_rpeak_detection(signal, fs):
    """Simple threshold-based R-peak detection as fallback."""
    from scipy.signal import find_peaks

    # High-pass filter approximation
    threshold = np.mean(signal) + 1.5 * np.std(signal)
    min_distance = int(0.4 * fs)  # Minimum 400ms between peaks

    peaks, _ = find_peaks(signal, height=threshold, distance=min_distance)
    return peaks


def assess_signal_quality(ecg_data):
    """Assess per-lead signal quality.

    Returns
    -------
    pd.DataFrame
        Quality metrics per lead.
    """
    signals = ecg_data["signals"]
    fs = ecg_data["fs"]
    lead_names = ecg_data["lead_names"]

    rows = []
    for idx, name in enumerate(lead_names):
        signal = signals[idx]
        quality = _compute_lead_quality(signal, fs)
        rows.append({
            "Lead": name,
            "Quality Index": quality["index"],
            "Interpretation": quality["interpretation"],
            "Dominant Noise": quality["noise_type"],
        })

    return pd.DataFrame(rows)


def _compute_lead_quality(signal, fs):
    """Compute quality index for a single lead."""
    from scipy.signal import welch

    # Quality checks
    score = 1.0
    noise_types = []

    # 1. Check for flat signal
    if np.std(signal) < 0.01:
        score -= 0.5
        noise_types.append("Flat signal")

    # 2. Check for baseline wander (low-freq power)
    if len(signal) > fs:
        f, pxx = welch(signal, fs=fs, nperseg=min(len(signal), fs * 2))
        low_freq_mask = f < 0.5
        total_power = np.sum(pxx)
        if total_power > 0:
            low_freq_power = np.sum(pxx[low_freq_mask]) / total_power
            if low_freq_power > 0.4:
                score -= 0.2
                noise_types.append("Baseline wander")

        # 3. Check for powerline noise (50/60 Hz)
        for freq in [50, 60]:
            freq_mask = (f >= freq - 1) & (f <= freq + 1)
            neighbor_mask = ((f >= freq - 5) & (f < freq - 1)) | ((f > freq + 1) & (f <= freq + 5))
            if np.any(freq_mask) and np.any(neighbor_mask):
                peak_power = np.max(pxx[freq_mask])
                neighbor_power = np.mean(pxx[neighbor_mask])
                if neighbor_power > 0 and peak_power / neighbor_power > 10:
                    score -= 0.15
                    noise_types.append(f"Powerline ({freq} Hz)")
                    break

    # 4. Check for signal clipping
    sig_range = np.max(signal) - np.min(signal)
    if sig_range > 0:
        at_max = np.sum(signal >= np.max(signal) * 0.99) / len(signal)
        at_min = np.sum(signal <= np.min(signal) * 0.99) / len(signal)
        if at_max > 0.01 or at_min > 0.01:
            score -= 0.2
            noise_types.append("Signal clipping")

    score = max(0.0, min(1.0, score))

    # Interpretation
    if score >= 0.8:
        interpretation = "\U0001f7e2 Excellent"
    elif score >= 0.6:
        interpretation = "\U0001f7e1 Acceptable"
    else:
        interpretation = "\U0001f534 Poor"

    return {
        "index": round(score, 2),
        "interpretation": interpretation,
        "noise_type": ", ".join(noise_types) if noise_types else "\u2014",
    }


def detect_known_ecg_dataset(ecg_data):
    """Try to identify if this is a known ECG research dataset.

    Returns
    -------
    dict or None
        Dataset info if recognized.
    """
    fs = ecg_data["fs"]
    n_leads = len(ecg_data["lead_names"])
    lead_names = set(ecg_data["lead_names"])

    for name, info in KNOWN_ECG_DATASETS.items():
        if info.get("fs") == fs and info.get("n_leads") == n_leads:
            return {"name": name, **info}

        # Match by lead names
        if "leads" in info and isinstance(info["leads"], list):
            dataset_leads = set(info["leads"])
            if dataset_leads == lead_names or dataset_leads.issubset(lead_names):
                return {"name": name, **info}

    return None


def extract_ecg_metadata(ecg_data, filepath, format_key, load_time=0):
    """Extract comprehensive ECG metadata.

    Returns
    -------
    dict
        Metadata fields for display.
    """
    import os

    duration_s = ecg_data["duration_s"]
    mins = int(duration_s // 60)
    secs = int(duration_s % 60)

    n_leads = len(ecg_data["lead_names"])
    if n_leads == 12:
        lead_type = "12-lead (Standard)"
    elif n_leads == 15:
        lead_type = "15-lead (Extended)"
    elif n_leads <= 3:
        lead_type = f"{n_leads}-lead (Holter/Ambulatory)"
    else:
        lead_type = f"{n_leads}-lead"

    # Patient info from comments
    comments = ecg_data.get("record_info", {}).get("comments", [])
    patient_info = "Not Available"
    for comment in comments:
        if "age" in comment.lower() or "sex" in comment.lower():
            patient_info = comment
            break

    return {
        "File Format": format_key.replace("ecg_", "").upper(),
        "File Size": f"{os.path.getsize(filepath) / 1024 / 1024:.1f} MB",
        "Load Time": f"{load_time:.1f} s",
        "Reader Used": f"load_ecg(format='{format_key}')",
        "Record Name": ecg_data.get("record_info", {}).get("record_name", "Unknown"),
        "Number of Leads": lead_type,
        "Sampling Frequency": f"{ecg_data['fs']} Hz",
        "Duration": f"{mins} min {secs} s",
        "Patient Info": patient_info,
        "Lead Names": ", ".join(ecg_data["lead_names"]),
    }

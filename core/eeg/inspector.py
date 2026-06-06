"""EEG Inspector - extracts metadata, channels, events, spectral features."""

import numpy as np
import pandas as pd
import mne

from config import EEG_BANDS, KNOWN_EEG_DATASETS


def extract_channel_info(raw):
    """Extract per-channel metadata from MNE Raw object.

    Returns
    -------
    pd.DataFrame
        Channel information table.
    """
    rows = []
    for idx, ch in enumerate(raw.info["chs"]):
        has_loc = not np.allclose(ch["loc"][:3], 0)
        rows.append({
            "Index": idx,
            "Name": ch["ch_name"],
            "Type": mne.channel_type(raw.info, idx).upper(),
            "Unit": _unit_label(ch.get("unit", 0)),
            "Bad": ch["ch_name"] in raw.info["bads"],
            "Has Location": has_loc,
            "X/Y/Z": (
                f"({ch['loc'][0]:.4f}, {ch['loc'][1]:.4f}, {ch['loc'][2]:.4f})"
                if has_loc else "N/A"
            ),
        })
    return pd.DataFrame(rows)


def _unit_label(unit_code):
    """Convert MNE unit code to human-readable label."""
    unit_map = {
        107: "\u00b5V",  # microvolts
        201: "T",  # tesla
        202: "fT",  # femtotesla
        0: "Unknown",
    }
    return unit_map.get(unit_code, f"Code {unit_code}")


def infer_reference(raw):
    """Heuristically determine referencing scheme.

    Returns
    -------
    str
        Description of inferred reference scheme.
    """
    ch_names = [ch.upper() for ch in raw.info["ch_names"]]

    # Check custom_ref_applied flag
    if raw.info.get("custom_ref_applied", False):
        return "Custom reference applied (flagged in file header)"

    # Check for reference channels
    ref_indicators = ["REF", "REFERENCE"]
    mastoid_indicators = ["M1", "M2", "A1", "A2", "TP9", "TP10"]

    has_ref = any(ind in ch_names for ind in ref_indicators)
    has_mastoid = any(ind in ch_names for ind in mastoid_indicators)

    if has_mastoid:
        return "Mastoid Reference (M1/M2 or A1/A2 detected)"
    elif has_ref:
        return "Linked Reference (REF channel present)"
    else:
        return "Common Average Reference (CAR) or hardware reference (no explicit ref channel)"


def extract_events(raw):
    """Extract events/annotations from EEG recording.

    Returns
    -------
    dict
        Keys: events_array, event_id, summary_df, has_events
    """
    try:
        events, event_id = mne.events_from_annotations(raw, verbose=False)
        if len(events) == 0:
            return {"has_events": False, "events_array": None, "event_id": None, "summary_df": None}

        # Build summary
        rows = []
        for label, eid in event_id.items():
            mask = events[:, 2] == eid
            count = mask.sum()
            first_sample = events[mask][0, 0] if count > 0 else 0
            last_sample = events[mask][-1, 0] if count > 0 else 0
            rows.append({
                "Event ID": eid,
                "Label": label,
                "Count": count,
                "First (s)": round(first_sample / raw.info["sfreq"], 2),
                "Last (s)": round(last_sample / raw.info["sfreq"], 2),
            })

        summary_df = pd.DataFrame(rows)
        return {
            "has_events": True,
            "events_array": events,
            "event_id": event_id,
            "summary_df": summary_df,
        }
    except Exception:
        return {"has_events": False, "events_array": None, "event_id": None, "summary_df": None}


def compute_psd(raw, fmin=0.5, fmax=50.0, n_fft=512):
    """Compute Power Spectral Density using Welch's method.

    Returns
    -------
    dict
        Keys: psds, freqs, band_powers, dominant_freqs
    """
    try:
        spectrum = raw.compute_psd(method="welch", fmin=fmin, fmax=fmax,
                                   n_fft=n_fft, verbose=False)
        psds, freqs = spectrum.get_data(return_freqs=True)
    except Exception:
        # Fallback for older MNE versions
        psds, freqs = mne.time_frequency.psd_welch(
            raw, fmin=fmin, fmax=fmax, n_fft=n_fft, verbose=False
        )

    # Compute relative band powers
    band_powers = _compute_band_powers(psds, freqs)

    # Dominant frequency per channel
    dominant_freqs = []
    for ch_psd in psds:
        dom_idx = np.argmax(ch_psd)
        dominant_freqs.append(freqs[dom_idx])

    return {
        "psds": psds,
        "freqs": freqs,
        "band_powers": band_powers,
        "dominant_freqs": dominant_freqs,
    }


def _compute_band_powers(psds, freqs):
    """Compute relative band power (%) for each channel and band.

    Returns
    -------
    pd.DataFrame
        Rows = channels, columns = band names with % values.
    """
    freq_res = freqs[1] - freqs[0]
    total_power = np.sum(psds, axis=1) * freq_res

    rows = []
    for ch_idx, ch_psd in enumerate(psds):
        row = {}
        for band_name, (flo, fhi) in EEG_BANDS.items():
            band_mask = (freqs >= flo) & (freqs < fhi)
            band_power = np.sum(ch_psd[band_mask]) * freq_res
            rel_power = (band_power / total_power[ch_idx]) * 100 if total_power[ch_idx] > 0 else 0
            row[f"{band_name}%"] = round(rel_power, 1)
        rows.append(row)

    return pd.DataFrame(rows)


def compute_faa(raw, left_ch="AF3", right_ch="AF4", band=(8, 13)):
    """Compute Frontal Alpha Asymmetry (FAA).

    FAA = ln(Power_right_alpha) - ln(Power_left_alpha)
    Positive FAA -> approach motivation / higher valence
    Negative FAA -> withdrawal motivation / lower valence

    Returns
    -------
    dict
        Keys: faa_value, interpretation, available
    """
    ch_names = raw.info["ch_names"]

    if left_ch not in ch_names or right_ch not in ch_names:
        return {"available": False, "faa_value": None, "interpretation": "FAA channels not available"}

    try:
        # Get alpha power for left and right channels
        left_idx = ch_names.index(left_ch)
        right_idx = ch_names.index(right_ch)

        spectrum = raw.compute_psd(method="welch", fmin=band[0], fmax=band[1],
                                   n_fft=512, verbose=False)
        psds, freqs = spectrum.get_data(return_freqs=True)

        left_power = np.mean(psds[left_idx])
        right_power = np.mean(psds[right_idx])

        if left_power <= 0 or right_power <= 0:
            return {"available": False, "faa_value": None, "interpretation": "Invalid power values"}

        faa = np.log(right_power) - np.log(left_power)

        if faa > 0:
            interpretation = "\U0001f7e2 Positive (Approach-oriented state)"
        elif faa < -0.1:
            interpretation = "\U0001f534 Negative (Withdrawal-oriented state)"
        else:
            interpretation = "\U0001f7e1 Neutral"

        return {"available": True, "faa_value": round(faa, 4), "interpretation": interpretation}
    except Exception as e:
        return {"available": False, "faa_value": None, "interpretation": f"Error: {str(e)}"}


def detect_known_dataset(raw):
    """Try to identify if this is a known research dataset.

    Returns
    -------
    dict or None
        Dataset info if recognized, None otherwise.
    """
    n_channels = len(raw.info["ch_names"])
    fs = raw.info["sfreq"]
    ch_names = set(raw.info["ch_names"])

    for name, info in KNOWN_EEG_DATASETS.items():
        # Match by channel count and sampling rate
        if info.get("channels") == n_channels and info.get("fs") == fs:
            return {"name": name, **info}

        # Match by channel names subset
        if "channel_names" in info:
            dataset_chs = set(info["channel_names"])
            if dataset_chs.issubset(ch_names) or ch_names.issubset(dataset_chs):
                return {"name": name, **info}

    return None


def extract_metadata(raw, filepath, format_key, load_time=0):
    """Extract comprehensive metadata from EEG recording.

    Returns
    -------
    dict
        Metadata fields suitable for display.
    """
    import os

    duration_s = raw.times[-1] if len(raw.times) > 0 else 0
    mins = int(duration_s // 60)
    secs = int(duration_s % 60)

    # Try to get recording date
    meas_date = raw.info.get("meas_date")
    rec_date = str(meas_date) if meas_date else "Not Available"

    # Try to get subject info
    subject_info = raw.info.get("subject_info", {})
    subject_id = subject_info.get("his_id", "Not Available") if subject_info else "Not Available"

    # Device info
    device = raw.info.get("device_info", {})
    device_str = device.get("type", "Not Available") if device else "Not Available"

    # Highpass / lowpass
    hp = raw.info.get("highpass", None)
    lp = raw.info.get("lowpass", None)
    prefilter = "Not in header"
    if hp is not None or lp is not None:
        parts = []
        if hp is not None and hp > 0:
            parts.append(f"HP: {hp} Hz")
        if lp is not None and lp > 0:
            parts.append(f"LP: {lp} Hz")
        if parts:
            prefilter = ", ".join(parts)

    return {
        "File Format": format_key.replace("eeg_", "").upper(),
        "File Size": f"{os.path.getsize(filepath) / 1024 / 1024:.1f} MB",
        "Load Time": f"{load_time:.1f} s",
        "Sampling Frequency": f"{raw.info['sfreq']} Hz",
        "Duration": f"{mins} min {secs} s",
        "Number of Channels": len(raw.info["ch_names"]),
        "Subject ID": subject_id,
        "Recording Date": rec_date,
        "Amplifier / Device": device_str,
        "Reference Scheme": infer_reference(raw),
        "Prefilter Info": prefilter,
    }

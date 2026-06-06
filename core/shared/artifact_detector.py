"""Artifact detection utilities for EEG and ECG signals."""

import numpy as np
from scipy.signal import welch


def detect_eeg_artifacts(raw):
    """Run all EEG artifact detection checks.

    Parameters
    ----------
    raw : mne.io.BaseRaw
        MNE Raw object (preloaded).

    Returns
    -------
    dict
        Artifact detection results for each check.
    """
    results = {}

    try:
        data = raw.get_data()
        fs = raw.info["sfreq"]
        ch_names = raw.info["ch_names"]
    except Exception:
        return {"error": True, "message": "Could not load data for artifact detection"}

    results["flat_channels"] = _detect_flat_channels(data, ch_names)
    results["noisy_channels"] = _detect_noisy_channels(data, ch_names)
    results["eog_artifacts"] = _detect_eog_artifacts(data, fs, ch_names)
    results["emg_artifacts"] = _detect_emg_artifacts(data, fs)
    results["electrode_pops"] = _detect_electrode_pops(data, fs)
    results["line_noise"] = _detect_line_noise(data, fs)

    return results


def _detect_flat_channels(data, ch_names, threshold=0.5e-6):
    """Flag channels where std(signal) < threshold."""
    stds = np.std(data, axis=1)
    flat = [ch_names[i] for i, s in enumerate(stds) if s < threshold]

    if len(flat) == 0:
        return {"status": "pass", "detail": "All channels active", "channels": []}
    else:
        return {"status": "fail", "detail": f"{len(flat)} flat channel(s): {', '.join(flat)}", "channels": flat}


def _detect_noisy_channels(data, ch_names, z_threshold=3.0):
    """Flag channels with abnormally high variance."""
    variances = np.var(data, axis=1)
    if len(variances) < 3:
        return {"status": "pass", "detail": "Insufficient channels for comparison", "channels": []}

    mean_var = np.mean(variances)
    std_var = np.std(variances)

    if std_var == 0:
        return {"status": "pass", "detail": "Uniform variance", "channels": []}

    z_scores = (variances - mean_var) / std_var
    noisy = [(ch_names[i], round(z_scores[i], 1)) for i in range(len(ch_names)) if z_scores[i] > z_threshold]

    if len(noisy) == 0:
        return {"status": "pass", "detail": "All channels within normal variance", "channels": []}
    else:
        detail = ", ".join([f"{ch} (z={z})" for ch, z in noisy])
        return {"status": "warn", "detail": f"{len(noisy)} noisy: {detail}", "channels": [n[0] for n in noisy]}


def _detect_eog_artifacts(data, fs, ch_names):
    """Detect eye blink artifacts using frontal channel amplitude."""
    # Look for frontal channels
    frontal = ["FP1", "FP2", "AF3", "AF4", "Fp1", "Fp2"]
    frontal_indices = [i for i, ch in enumerate(ch_names) if ch.upper() in [f.upper() for f in frontal]]

    if len(frontal_indices) == 0:
        # Use first two channels as proxy
        frontal_indices = [0] if len(ch_names) > 0 else []

    if len(frontal_indices) == 0:
        return {"status": "unknown", "detail": "No frontal channels available"}

    # Count high-amplitude spikes (potential blinks)
    threshold = 100e-6  # 100 uV
    blink_count = 0
    for idx in frontal_indices:
        signal = data[idx]
        peaks = np.abs(signal) > threshold
        # Count transitions as individual blinks
        transitions = np.diff(peaks.astype(int))
        blink_count += np.sum(transitions == 1)

    blink_count = blink_count // max(len(frontal_indices), 1)

    if blink_count == 0:
        return {"status": "pass", "detail": "No blinks detected"}
    elif blink_count < 20:
        return {"status": "low", "detail": f"~{blink_count} blinks detected"}
    else:
        return {"status": "warn", "detail": f"~{blink_count} blinks detected (consider EOG removal)"}


def _detect_emg_artifacts(data, fs):
    """Detect muscle artifacts via high-frequency power ratio."""
    gamma_ratios = []

    for ch_data in data:
        if len(ch_data) < int(fs * 2):
            continue
        f, pxx = welch(ch_data, fs=fs, nperseg=min(len(ch_data), int(fs * 2)))
        total_power = np.sum(pxx)
        if total_power == 0:
            continue
        gamma_mask = f >= 30
        gamma_power = np.sum(pxx[gamma_mask])
        gamma_ratios.append(gamma_power / total_power * 100)

    if len(gamma_ratios) == 0:
        return {"status": "unknown", "detail": "Could not compute gamma ratio"}

    mean_gamma = np.mean(gamma_ratios)

    if mean_gamma < 20:
        return {"status": "pass", "detail": f"Gamma ratio: {mean_gamma:.1f}% (low)"}
    elif mean_gamma < 40:
        return {"status": "low", "detail": f"Gamma ratio: {mean_gamma:.1f}% (moderate)"}
    else:
        return {"status": "warn", "detail": f"Gamma ratio: {mean_gamma:.1f}% (high - EMG contamination likely)"}


def _detect_electrode_pops(data, fs):
    """Detect sudden large-amplitude jumps (electrode pops)."""
    pop_count = 0
    threshold = 200e-6  # 200 uV
    samples_5ms = max(int(0.005 * fs), 1)

    for ch_data in data:
        # Compute derivative
        diff = np.abs(np.diff(ch_data))
        # Find jumps larger than threshold in 5ms window
        for i in range(0, len(diff) - samples_5ms, samples_5ms):
            window = diff[i:i + samples_5ms]
            if np.max(window) > threshold:
                pop_count += 1

    if pop_count == 0:
        return {"status": "pass", "detail": "No electrode pops detected"}
    elif pop_count < 5:
        return {"status": "warn", "detail": f"{pop_count} potential electrode pop(s)"}
    else:
        return {"status": "fail", "detail": f"{pop_count} electrode pops detected"}


def _detect_line_noise(data, fs):
    """Check for 50 Hz or 60 Hz powerline noise."""
    if fs < 100:
        return {"status": "unknown", "detail": "Sampling rate too low to detect line noise"}

    for ch_data in data[:min(len(data), 5)]:  # Check first 5 channels
        if len(ch_data) < int(fs * 2):
            continue
        f, pxx = welch(ch_data, fs=fs, nperseg=min(len(ch_data), int(fs * 2)))

        for freq in [50, 60]:
            if freq > fs / 2:
                continue
            freq_mask = (f >= freq - 1) & (f <= freq + 1)
            neighbor_mask = ((f >= freq - 5) & (f < freq - 1)) | ((f > freq + 1) & (f <= freq + 5))

            if not np.any(freq_mask) or not np.any(neighbor_mask):
                continue

            peak_power = np.max(pxx[freq_mask])
            neighbor_power = np.mean(pxx[neighbor_mask])

            if neighbor_power > 0:
                ratio_db = 10 * np.log10(peak_power / neighbor_power)
                if ratio_db > 10:
                    return {
                        "status": "fail",
                        "detail": f"{freq} Hz peak detected (+{ratio_db:.0f} dB above neighbors)"
                    }

    return {"status": "pass", "detail": "No significant line noise"}


def detect_ecg_artifacts(ecg_data):
    """Run all ECG artifact detection checks.

    Parameters
    ----------
    ecg_data : dict
        Standardized ECG data dict.

    Returns
    -------
    dict
        Artifact detection results.
    """
    signals = ecg_data["signals"]
    fs = ecg_data["fs"]

    results = {}
    results["baseline_wander"] = _check_baseline_wander(signals, fs)
    results["powerline_noise"] = _check_ecg_powerline(signals, fs)
    results["motion_artifacts"] = _check_motion(signals, fs)
    results["signal_clipping"] = _check_clipping(signals)
    results["lead_reversal"] = _check_lead_reversal(signals, ecg_data.get("lead_names", []))
    results["missing_beats"] = _check_rr_gaps(signals, fs)
    results["pacemaker_spikes"] = _check_pacemaker(signals, fs)

    return results


def _check_baseline_wander(signals, fs):
    """Check for low-frequency drift < 0.5 Hz."""
    for sig in signals[:min(len(signals), 3)]:
        if len(sig) < int(fs * 4):
            continue
        f, pxx = welch(sig, fs=fs, nperseg=min(len(sig), int(fs * 4)))
        total_power = np.sum(pxx)
        if total_power == 0:
            continue
        low_mask = f < 0.5
        low_power = np.sum(pxx[low_mask]) / total_power
        if low_power > 0.3:
            return {"status": "warn", "detail": f"Baseline wander detected (LF power: {low_power*100:.0f}%)"}

    return {"status": "pass", "detail": "No significant baseline wander"}


def _check_ecg_powerline(signals, fs):
    """Check for 50/60 Hz interference in ECG."""
    if fs < 100:
        return {"status": "unknown", "detail": "Sampling rate too low"}

    for sig in signals[:min(len(signals), 3)]:
        if len(sig) < int(fs * 2):
            continue
        f, pxx = welch(sig, fs=fs, nperseg=min(len(sig), int(fs * 2)))

        for freq in [50, 60]:
            if freq > fs / 2:
                continue
            freq_mask = (f >= freq - 1) & (f <= freq + 1)
            neighbor_mask = ((f >= freq - 5) & (f < freq - 1)) | ((f > freq + 1) & (f <= freq + 5))

            if not np.any(freq_mask) or not np.any(neighbor_mask):
                continue

            peak_power = np.max(pxx[freq_mask])
            neighbor_power = np.mean(pxx[neighbor_mask])

            if neighbor_power > 0 and peak_power / neighbor_power > 10:
                return {"status": "fail", "detail": f"{freq} Hz interference detected"}

    return {"status": "pass", "detail": "No powerline interference"}


def _check_motion(signals, fs):
    """Check for motion artifacts (sudden amplitude changes)."""
    artifact_count = 0
    for sig in signals[:min(len(signals), 3)]:
        std = np.std(sig)
        if std == 0:
            continue
        diff = np.abs(np.diff(sig))
        threshold = 5 * std / fs  # Normalized threshold
        artifact_count += np.sum(diff > threshold * fs)

    if artifact_count < 10:
        return {"status": "pass", "detail": "No significant motion artifacts"}
    elif artifact_count < 50:
        return {"status": "warn", "detail": f"{artifact_count} potential motion artifacts"}
    else:
        return {"status": "fail", "detail": f"{artifact_count} motion artifacts detected"}


def _check_clipping(signals):
    """Check if signal is clipped at ADC limits."""
    for sig in signals:
        sig_max = np.max(sig)
        sig_min = np.min(sig)
        sig_range = sig_max - sig_min
        if sig_range == 0:
            continue

        at_max = np.sum(np.abs(sig - sig_max) < sig_range * 0.001) / len(sig)
        at_min = np.sum(np.abs(sig - sig_min) < sig_range * 0.001) / len(sig)

        if at_max > 0.01 or at_min > 0.01:
            return {"status": "fail", "detail": "Signal clipping detected"}

    return {"status": "pass", "detail": "No signal clipping"}


def _check_lead_reversal(signals, lead_names):
    """Check for lead reversal (Lead II should have positive QRS)."""
    if "II" not in lead_names and "MLII" not in lead_names:
        return {"status": "unknown", "detail": "Lead II not available for check"}

    lead_ii_idx = None
    for idx, name in enumerate(lead_names):
        if name in ("II", "MLII"):
            lead_ii_idx = idx
            break

    if lead_ii_idx is None:
        return {"status": "unknown", "detail": "Lead II not found"}

    sig = signals[lead_ii_idx]
    # QRS should be predominantly positive in lead II
    mean_val = np.mean(sig)
    if mean_val < -np.std(sig):
        return {"status": "warn", "detail": "Possible lead reversal (Lead II predominantly negative)"}

    return {"status": "pass", "detail": "Lead orientation appears correct"}


def _check_rr_gaps(signals, fs):
    """Check for missing beats (RR > 2.5 s)."""
    from scipy.signal import find_peaks

    # Use first lead for R-peak detection
    sig = signals[0]
    threshold = np.mean(sig) + 1.0 * np.std(sig)
    min_distance = int(0.4 * fs)

    peaks, _ = find_peaks(sig, height=threshold, distance=min_distance)

    if len(peaks) < 2:
        return {"status": "unknown", "detail": "Insufficient peaks for analysis"}

    rr = np.diff(peaks) / fs
    long_gaps = np.sum(rr > 2.5)

    if long_gaps == 0:
        return {"status": "pass", "detail": "No missing beats detected"}
    else:
        return {"status": "warn", "detail": f"{long_gaps} gap(s) > 2.5 s (possible missed beats)"}


def _check_pacemaker(signals, fs):
    """Check for pacemaker spikes (narrow high-amplitude spikes)."""
    # Pacemaker spikes are very short (<2ms) and high amplitude
    spike_count = 0
    samples_2ms = max(int(0.002 * fs), 1)

    for sig in signals[:min(len(signals), 2)]:
        diff = np.diff(sig)
        std = np.std(diff)
        if std == 0:
            continue

        # Look for very sharp spikes
        for i in range(len(diff) - samples_2ms):
            window = diff[i:i + samples_2ms]
            if np.max(np.abs(window)) > 10 * std:
                spike_count += 1

    if spike_count == 0:
        return {"status": "pass", "detail": "No pacemaker spikes detected"}
    elif spike_count < 5:
        return {"status": "unknown", "detail": f"{spike_count} possible pacemaker spike(s)"}
    else:
        return {"status": "warn", "detail": f"{spike_count} pacemaker spikes detected"}

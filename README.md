# 🧠 Agent 1: Dataset Inspector

**NeuroInspect** — A research-grade biomedical dataset inspection tool for EEG and ECG signal analysis. Built for Biomedical Engineering postgraduate researchers working on brain-computer interfaces, emotion recognition, and cardiac arrhythmia detection.

---

## 🎯 Overview

NeuroInspect autonomously identifies, reads, parses, and reports on EEG and ECG datasets uploaded by a researcher. It wraps **MNE-Python** (EEG) and **WFDB + NeuroKit2** (ECG) into a clean, interactive Streamlit application that non-programmers can use, while giving expert researchers the full technical depth they need.

Every output is designed to be **research-publication quality**.

---

## ✨ Key Features

### 🧠 EEG Analysis (8-Tab Dashboard)
- **Overview** — File metadata, sampling rate, duration, channel count, known dataset detection
- **Channels** — Per-channel metadata table, reference scheme detection, montage visualization
- **Events** — Event/annotation parsing, trial summary, timeline visualization, dataset label decoding
- **Frequency** — PSD (Welch), relative band power (Delta/Theta/Alpha/Beta/Gamma), Frontal Alpha Asymmetry (FAA)
- **Artifacts** — Flat channels, noisy channels, EOG blinks, EMG contamination, electrode pops, line noise (50/60 Hz)
- **Topography** — Channel correlation matrix, coherence analysis
- **Quality Score** — 100-point weighted rubric with actionable recommendations
- **Export** — PDF, DOCX (journal-ready A4 format), JSON (machine-readable for downstream pipelines)

### 🫀 ECG Analysis (8-Tab Dashboard)
- **Overview** — File metadata, lead configuration, known dataset detection
- **Leads** — Per-lead info table, multi-lead signal preview (Plotly)
- **Annotations** — Beat annotation parsing (WFDB), beat type summary (N/V/A/F/Q), timeline
- **Signal Quality** — Per-lead quality index (0–1), noise type classification
- **Artifacts** — Baseline wander, powerline noise, motion artifacts, signal clipping, lead reversal, missing beats, pacemaker spikes
- **R-Peak Stats** — R-peak detection (NeuroKit2), HR classification, HRV metrics (SDNN, RMSSD, pNN50), RR tachogram, Poincaré plot
- **Quality Score** — 100-point weighted rubric with recommendations
- **Export** — PDF, DOCX, JSON

### 🤖 Auto-Detection & Known Dataset Recognition
- **Format Router** — Automatically identifies EEG vs ECG by file extension + magic byte inspection
- **Known EEG Datasets**: DREAMER, DEAP, SEED, MAHNOB-HCI, PhysioNet Motor Imagery, BCI Competition IV
- **Known ECG Datasets**: MIT-BIH Arrhythmia, PTB Diagnostic, PTB-XL, CPSC 2018, PhysioNet Challenge

---

## 🛠 Technology Stack

| Component | Technology |
|-----------|-----------|
| Frontend / UI | Streamlit ≥1.35.0 |
| EEG Backend | MNE-Python ≥1.7.0 |
| ECG Backend | WFDB ≥4.1.0, NeuroKit2 ≥0.2.0 |
| Signal Processing | SciPy ≥1.13.0, NumPy ≥1.26.0 |
| Data Handling | Pandas ≥2.2.0, h5py ≥3.11.0 |
| Visualization | Plotly ≥5.22.0, Matplotlib ≥3.9.0 |
| Report Export | ReportLab ≥4.2.0 (PDF), python-docx ≥1.1.0 (DOCX) |
| Testing | pytest |

---

## 📁 Project Structure

```
neuroinspect/
├── app.py                          # Streamlit entry point
├── config.py                       # Constants, bands, known datasets, theme
├── requirements.txt
├── core/
│   ├── format_router.py            # EEG/ECG auto-detection & routing
│   ├── eeg/
│   │   ├── reader.py               # MNE-based multi-format reader
│   │   ├── inspector.py            # Channels, PSD, FAA, events
│   │   └── report_builder.py       # Full EEG report assembly + quality scoring
│   ├── ecg/
│   │   ├── reader.py               # WFDB / NeuroKit2 / CSV / NumPy reader
│   │   ├── inspector.py            # R-peaks, HRV, annotations, signal quality
│   │   └── report_builder.py       # Full ECG report assembly + quality scoring
│   └── shared/
│       ├── artifact_detector.py    # 6 EEG + 7 ECG artifact checks
│       └── exporter.py             # PDF / DOCX / JSON export
├── ui/
│   ├── landing.py                  # Upload screen with sidebar controls
│   ├── eeg_dashboard.py            # 8-tab EEG inspection dashboard
│   ├── ecg_dashboard.py            # 8-tab ECG inspection dashboard
│   ├── components.py               # Reusable cards, badges, gauge charts
│   └── styles.py                   # Dark scientific theme CSS
└── tests/
    ├── conftest.py                 # Shared fixtures (sample EEG/ECG data)
    ├── test_format_router.py
    ├── test_eeg_reader.py
    ├── test_eeg_inspector.py
    ├── test_ecg_reader.py
    ├── test_ecg_inspector.py
    ├── test_artifact_detector.py
    └── test_quality_scorer.py
```

---

## 📦 Supported File Formats

### EEG
| Format | Extension | Reader |
|--------|-----------|--------|
| European Data Format | `.edf`, `.edf+` | `mne.io.read_raw_edf` |
| BioSemi Data Format | `.bdf` | `mne.io.read_raw_bdf` |
| General Data Format | `.gdf` | `mne.io.read_raw_gdf` |
| EEGLAB | `.set`, `.fdt` | `mne.io.read_raw_eeglab` |
| BrainVision | `.vhdr`, `.vmrk`, `.eeg` | `mne.io.read_raw_brainvision` |
| MNE/Neuromag FIF | `.fif` | `mne.io.read_raw_fif` |
| Neuroscan | `.cnt` | `mne.io.read_raw_cnt` |
| MATLAB | `.mat` | `scipy.io` / `pymatreader` |
| HDF5 | `.h5`, `.hdf5` | `h5py` |
| XDF (LSL) | `.xdf` | `pyxdf` |

### ECG
| Format | Extension | Reader |
|--------|-----------|--------|
| PhysioNet WFDB | `.dat`, `.hea`, `.atr` | `wfdb.rdrecord` |
| CSV | `.csv` | `pandas` |
| NumPy | `.npy`, `.npz` | `numpy` |
| MATLAB | `.mat` | `scipy.io` / `pymatreader` |
| EDF (ECG) | `.edf` | `mne.io.read_raw_edf` |
| JSON | `.json` | `json` |
| HDF5 | `.h5`, `.hdf5` | `h5py` |

---

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/hariomaggarwal11/neuroinspect.git
cd neuroinspect

# Install dependencies
pip install -r requirements.txt

# Run the application
streamlit run app.py

# Open in browser: http://localhost:8501
```

---

## 🧪 Running Tests

```bash
cd neuroinspect
pytest tests/ -v
```

**55 tests** covering format routing, EEG/ECG readers, inspectors, artifact detection, and quality scoring — all passing.

---

## 🎨 UI Theme

NeuroInspect uses a **precision-scientific dark theme** — the aesthetic of a high-end neuroimaging workstation:

- Deep navy background (`#0a0e1a`)
- Electric cyan accent for EEG (`#00d4ff`)
- Vital-sign red accent for ECG (`#ff4d6d`)
- JetBrains Mono for data display
- Inter for body text
- Status badges: 🟢 PASS / 🟡 WARN / 🔴 FAIL

---

## 📊 Quality Scoring

### EEG Quality Score (100 pts)
| Criterion | Points |
|-----------|--------|
| Sampling frequency ≥ 128 Hz | 15 |
| Channel count ≥ 8 | 10 |
| No flat/dead channels | 15 |
| No line noise | 15 |
| EOG artifacts low | 10 |
| EMG contamination low | 10 |
| Duration ≥ 5 minutes | 10 |
| Events/labels present | 10 |
| Channel locations available | 5 |

### ECG Quality Score (100 pts)
| Criterion | Points |
|-----------|--------|
| Sampling frequency ≥ 250 Hz | 15 |
| Standard lead names present | 10 |
| Mean lead quality ≥ 0.7 | 20 |
| No signal clipping | 10 |
| No powerline noise | 10 |
| Annotations present | 15 |
| R-peak detection successful | 10 |
| Duration ≥ 10 seconds | 10 |

---

## 🔬 Research Features

- **Frontal Alpha Asymmetry (FAA)**: Validated biomarker for emotional valence — `ln(Right α) - ln(Left α)`
- **HRV Analysis**: SDNN, RMSSD, pNN50, Mean RR with clinical reference ranges
- **Poincaré Plot**: RR[n] vs RR[n+1] scatter for nonlinear HRV visualization
- **Band Power Analysis**: Relative power in Delta/Theta/Alpha/Beta/Gamma bands per channel
- **Known Dataset Auto-Recognition**: Automatically identifies DREAMER, DEAP, MIT-BIH, PTB-XL and pre-fills label mappings

---

## 📄 Export Formats

| Format | Use Case |
|--------|----------|
| **PDF** | Publication-ready report with tables, metrics, and quality score |
| **DOCX** | Editable Word document (A4, Times New Roman 12pt) for journal submission |
| **JSON** | Machine-readable format for feeding into Agent 2 (Pipeline Builder) |

---

## 🏗 Part of the BioMed Research Agent Suite

NeuroInspect (Agent 1) is the **Dataset Inspector** — the first stage in a multi-agent biomedical signal processing pipeline. Its JSON export feeds directly into **Agent 2: Pipeline Builder** for automated preprocessing and feature extraction.

---

## 📝 License

This project is part of the BioMed Research Agent Suite.

---

*NeuroInspect v1.0 · Powered by MNE-Python + WFDB + NeuroKit2*

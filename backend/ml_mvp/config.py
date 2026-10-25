"""Deterministic configuration for the compact CinC 2017 data pipeline."""

from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BACKEND_DIR / "data"
RAW_DIR = DATA_DIR / "raw" / "cinc2017"
PROCESSED_DIR = DATA_DIR / "processed"

SEED = 42
SOURCE_NAME = "PhysioNet/CinC Challenge 2017"
SOURCE_VERSION = "1.0.0"
SOURCE_ACCESS_DATE = "2026-10-25"
SOURCE_PAGE_URL = "https://physionet.org/content/challenge-2017/1.0.0/"
SOURCE_LABELS_URL = "https://physionet.org/files/challenge-2017/1.0.0/REFERENCE-v3.csv"
SOURCE_ARCHIVE_URL = "https://physionet.org/files/challenge-2017/1.0.0/training2017.zip"
SOURCE_ARCHIVE_MIRROR_URL = "https://physionet-open.s3.amazonaws.com/challenge-2017/1.0.0/training2017.zip"
SOURCE_LICENSE = "No explicit dataset license statement found on the source page; verify terms before redistribution"
SOURCE_LICENSE_URL = SOURCE_PAGE_URL
SOURCE_CITATION_URL = "https://physionet.org/content/challenge-2017/1.0.0/#citation"

ORIGINAL_FS_HZ = 300
TARGET_FS_HZ = 125
WINDOW_SECONDS = 10
WINDOW_SAMPLES = TARGET_FS_HZ * WINDOW_SECONDS
BANDPASS_LOW_HZ = 0.5
BANDPASS_HIGH_HZ = 40.0
BANDPASS_ORDER = 4

TARGET_NORMAL = 700
TARGET_AF = 300
SPLIT_FRACTIONS = {"train": 0.70, "validation": 0.15, "test": 0.15}
DOWNLOAD_TIMEOUT_SECONDS = 120
PIPELINE_DEADLINE_SECONDS = 600

# Task 2.1 lightweight model, motion, fusion, and CLI configuration.
MODELS_DIR = BACKEND_DIR / "models"
COHORT_FILE = PROCESSED_DIR / "cinc2017_cohort.npz"
MVP_MODEL_FILE = MODELS_DIR / "mvp_model.pkl"
MVP_MODEL_META_FILE = MODELS_DIR / "mvp_model.json"
MVP_METRICS_FILE = MODELS_DIR / "mvp_metrics.json"
MVP_RUN_LOG_FILE = PROCESSED_DIR / "task_2_1_run_log.json"
MOTION_FILE = PROCESSED_DIR / "hapt_motion_subset.npz"
MOTION_MANIFEST_FILE = PROCESSED_DIR / "motion_manifest.json"
PERSONA_INPUTS_FILE = PROCESSED_DIR / "mvp_personas.json"

MOTION_RAW_DIR = DATA_DIR / "raw" / "uci_hapt"
HAPT_ARCHIVE_FILE = MOTION_RAW_DIR / "hapt.zip"
HAPT_SOURCE_URL = "https://archive.ics.uci.edu/static/public/341/smartphone+based+recognition+of+human+activities+and+postural+transitions.zip"
HAPT_SOURCE_PAGE_URL = "https://archive.ics.uci.edu/dataset/341/smartphone+based+recognition+of+human+activities+and+postural+transitions"
HAPT_VERSION = "UCI repository snapshot accessed 2026-10-25"
HAPT_LICENSE = "Creative Commons Attribution 4.0 International (CC BY 4.0)"
HAPT_LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/legalcode"
HAPT_CITATION_URL = HAPT_SOURCE_PAGE_URL
HAPT_MAX_WINDOWS = 12

MIN_R_PEAKS = 3
RR_MIN_MS = 250.0
RR_MAX_MS = 2000.0
MODEL_TARGET_SENSITIVITY = 0.90

MOTION_FS_HZ = 50
MOTION_WINDOW_SAMPLES = MOTION_FS_HZ * WINDOW_SECONDS
MOTION_VERTICAL_AXIS = 0
MOTION_DYNAMIC_ENERGY_G2 = 0.01
MOTION_LYING_ANGLE_DEG = 60.0
MOTION_ARTIFACT_MAG_VAR_G2 = 0.02
MOTION_ARTIFACT_JERK_RMS_GPS = 0.75
MOTION_INACTIVITY_ENERGY_G2 = 0.002
MOTION_IMPACT_PEAK_G = 2.5
MOTION_COLLAPSE_GAP_SECONDS = 10.0
PROLONGED_INACTIVITY_SECONDS = 60.0

FUSION_K = 3
FUSION_N = 5
FUSION_COINCIDENCE_SECONDS = 300.0
FUSION_DATA_QUALITY_FRACTION = 0.5
DEMO_COUNTDOWN_SECONDS = 0.20
PRODUCTION_COUNTDOWN_ANALOGUE_SECONDS = 30

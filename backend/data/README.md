# Real public data for the isolated ECG + motion MVP

## Achieved ECG cohort

- Source: [PhysioNet/CinC Challenge 2017](https://physionet.org/content/challenge-2017/1.0.0/), version 1.0.0, accessed 2026-10-25.
- Achieved rows: **1,000** (700 Normal, 300 AF).
- Record splits: train 700, validation 150, test 150.
- Shortfall/fallback: none; the requested compact cohort was reached.
- Every cohort row is real (`isSynthetic: false`); no record was padded, duplicated, generated, or relabeled.
- Signal/label downloads: [training archive](https://physionet.org/files/challenge-2017/1.0.0/training2017.zip) and [REFERENCE-v3.csv](https://physionet.org/files/challenge-2017/1.0.0/REFERENCE-v3.csv).
- License note: [the source page does not state an explicit dataset license; redistribution terms must be verified](https://physionet.org/content/challenge-2017/1.0.0/).
- Citation: [PhysioNet source citation section](https://physionet.org/content/challenge-2017/1.0.0/#citation).

The pipeline uses seed 42, selects only Normal/AF records with a usable first 10-second signal, applies an order-4 zero-phase 0.5–40 Hz bandpass at 300 Hz, resamples to 125 Hz, and stores one 1,250-sample float32 window per record. Splits are deterministic and stratified at 70/15/15 by record.

## Achieved motion fixture

- Source: [UCI Smartphone-Based Recognition of Human Activities and Postural Transitions (HAPT)](https://archive.ics.uci.edu/dataset/341/smartphone+based+recognition+of+human+activities+and+postural+transitions), repository snapshot accessed 2026-10-25.
- License: [Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/legalcode).
- Achieved rows: **8** real 10-second accelerometer/gyroscope windows at 50 Hz from subject 1, experiment 1.
- Activities/transitions: walking, walking upstairs, walking downstairs, sitting, standing, lying, sit-to-lie, and stand-to-lie.
- Extraction: first finite window for each required activity; transition windows are centered on the labeled transition.
- Exact source offsets, derived motion features, thresholds, archive hash, and processed-file hash are in `processed/motion_manifest.json`.

## Reproduction and checks

From `backend/` on Windows:

```powershell
conda run --no-capture-output -n hack1 python -m ml_mvp.pipeline
conda run --no-capture-output -n hack1 python -m ml_mvp.pipeline --check
conda run --no-capture-output -n hack1 python -m ml_mvp.build_mvp
```

Raw downloads are cached under `backend/data/raw/` and are intentionally gitignored. Processed files and canonical manifests are committed only when compact.

## Provenance and limitations

- CinC 2017 provides rhythm labels, not stroke diagnoses or stroke-onset labels. The MVP supports only AF-like rhythm experiments and is non-diagnostic.
- CinC 2017 publishes no patient identifiers. Treating each record as one patient/group is an explicit MVP assumption and cannot prove patient-disjointness.
- Device and demographic metadata are limited, so subgroup performance and bias cannot be assessed.
- The retained ECG window is the first usable 10 seconds of each selected record; it is not longitudinal evidence.
- UCI HAPT motion comes from a waist-worn smartphone in scripted laboratory activities, not a wrist wearable in daily life.
- Controlled HAPT lie-down transitions are not falls or stroke events.
- The motion fixture is intentionally bounded to eight windows and one subject; it is not a motion-model validation set.
- ECG and motion windows come from different people and datasets. Their pairing is a deterministic demonstration construction.
- No public paired actual stroke-onset ECG/motion dataset is used.
- File hashes, exact ECG record IDs, exclusions, preprocessing parameters, and achieved counts are in `processed/data_manifest.json` and `processed/split_manifest.json`.

"""
03_extract_features_v2.py

Fixes a real data-leakage problem found in the first training run: FSC22's 75
clips per class are actually ~8 sub-clips (A-H) cut from only ~9-10 unique
source recordings. A plain random split let sub-clips from the same source
recording land in both train and val/test, so val "accuracy" wasn't measuring
generalization to new recordings -- it was measuring memorization of the same
handful of recordings. Root cause of last run's overfit-from-epoch-1 pattern.

This version:
  1. Extracts a `group_id` per clip = the base source recording ID
     (e.g. "17548__A.wav" and "17548_B.wav" both -> group "17548")
  2. Uses StratifiedGroupKFold so the split is class-balanced AND no source
     recording's sub-clips appear in more than one split.

Re-run this before re-running training. Old features/*.npy from the previous
run should be considered invalid for evaluating generalization.
"""

import os
import re
import glob
import numpy as np
import pandas as pd
import librosa
from sklearn.model_selection import StratifiedGroupKFold

from importlib.util import spec_from_file_location, module_from_spec

def _load_mapping_module():
    spec = spec_from_file_location("label_mapping", os.path.join(os.path.dirname(__file__), "02_build_label_mapping.py"))
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

label_mod = _load_mapping_module()

# ---- EDIT THESE to match your actual paths (same as before) ----
AUDIO_DIR = "fsc22_data/Audio Wise V1.0-20220916T202003Z-001/Audio Wise V1.0"  # adjust to your real folder
METADATA_CSV = "fsc22_data/Metadata-20220916T202011Z-001/Metadata/Metadata V1.0 FSC22.csv"
OUT_DIR = "features"
SAMPLE_RATE = 16000
N_MELS = 40
N_FFT = 1024
HOP_LENGTH = 512
CLIP_DURATION_SEC = 5
# ------------------------------------------------------------------

TARGET_LEN = SAMPLE_RATE * CLIP_DURATION_SEC


def extract_log_mel(filepath):
    y, sr = librosa.load(filepath, sr=SAMPLE_RATE)
    if len(y) < TARGET_LEN:
        y = np.pad(y, (0, TARGET_LEN - len(y)))
    else:
        y = y[:TARGET_LEN]
    mel = librosa.feature.melspectrogram(
        y=y, sr=SAMPLE_RATE, n_mels=N_MELS, n_fft=N_FFT, hop_length=HOP_LENGTH
    )
    log_mel = librosa.power_to_db(mel, ref=np.max)
    return log_mel.astype(np.float32)


def base_source_id(source_filename: str) -> str:
    """'17548__A.wav' -> '17548', '17717_B.wav' -> '17717'. Falls back to the
    filename itself if the A-H suffix pattern isn't found (some FSC22 sources
    aren't split into sub-clips)."""
    m = re.sub(r'_+[A-Za-z]\.wav$', '', source_filename)
    return m if m != source_filename else source_filename.replace(".wav", "")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    meta = pd.read_csv(METADATA_CSV)
    id_to_label = label_mod.build_mapping_from_metadata(meta)

    # Build DatasetFileName -> group_id lookup from the metadata (this is why we
    # need the metadata CSV, not just the filenames on disk)
    name_col_candidates = [c for c in meta.columns if "dataset" in c.lower() and "file" in c.lower()]
    src_col_candidates = [c for c in meta.columns if "source" in c.lower() and "file" in c.lower()]
    if not name_col_candidates or not src_col_candidates:
        raise ValueError(f"Could not find Dataset File Name / Source File Name columns. Got: {list(meta.columns)}")
    dataset_col, source_col = name_col_candidates[0], src_col_candidates[0]

    filename_to_group = {}
    for _, row in meta.iterrows():
        filename_to_group[str(row[dataset_col])] = base_source_id(str(row[source_col]))

    files = glob.glob(os.path.join(AUDIO_DIR, "*.wav"))
    print(f"Found {len(files)} audio files.")

    X, y_labels, groups, skipped = [], [], [], 0
    for f in files:
        fname = os.path.basename(f)
        class_id = fname.split("_")[0]
        label = id_to_label.get(class_id, "UNMAPPED")
        group = filename_to_group.get(fname)
        if label == "UNMAPPED" or group is None:
            skipped += 1
            continue
        try:
            feat = extract_log_mel(f)
        except Exception as e:
            print(f"  Skipping {f}: {e}")
            skipped += 1
            continue
        X.append(feat)
        y_labels.append(label)
        groups.append(group)

    print(f"Extracted features for {len(X)} clips, skipped {skipped}.")

    X = np.stack(X)
    classes = sorted(set(y_labels))
    label_to_idx = {c: i for i, c in enumerate(classes)}
    y = np.array([label_to_idx[l] for l in y_labels])
    groups = np.array(groups)

    n_unique_groups = len(set(groups))
    print(f"\nUnique source recordings (groups): {n_unique_groups} "
          f"(this is your TRUE data diversity, not {len(X)})")

    # StratifiedGroupKFold: 5 folds -> holds out ~20% per fold, class-balanced,
    # groups never split across folds. We take fold 0 as test, fold 1 as val,
    # rest as train -- giving roughly 60/20/20 by GROUP (not by clip count,
    # which will vary slightly since group sizes differ).
    sgkf = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
    folds = list(sgkf.split(X, y, groups))

    test_idx = folds[0][1]
    val_idx = folds[1][1]
    train_idx = np.array(sorted(set(range(len(X))) - set(test_idx) - set(val_idx)))

    X_train, y_train = X[train_idx], y[train_idx]
    X_val, y_val = X[val_idx], y[val_idx]
    X_test, y_test = X[test_idx], y[test_idx]

    # sanity check: no group should appear in more than one split
    g_train, g_val, g_test = set(groups[train_idx]), set(groups[val_idx]), set(groups[test_idx])
    overlap = (g_train & g_val) | (g_train & g_test) | (g_val & g_test)
    assert not overlap, f"LEAKAGE: groups appear in multiple splits: {overlap}"
    print("Verified: no source recording appears in more than one split (no leakage).")

    print("\nSimplified class distribution (train / val / test):")
    for c in classes:
        ci = label_to_idx[c]
        print(f"  {c}: {sum(y_train==ci)} / {sum(y_val==ci)} / {sum(y_test==ci)}")

    np.save(os.path.join(OUT_DIR, "X_train.npy"), X_train)
    np.save(os.path.join(OUT_DIR, "y_train.npy"), y_train)
    np.save(os.path.join(OUT_DIR, "X_val.npy"), X_val)
    np.save(os.path.join(OUT_DIR, "y_val.npy"), y_val)
    np.save(os.path.join(OUT_DIR, "X_test.npy"), X_test)
    np.save(os.path.join(OUT_DIR, "y_test.npy"), y_test)
    with open(os.path.join(OUT_DIR, "classes.txt"), "w") as fh:
        fh.write("\n".join(classes))

    print(f"\nSaved GROUP-SAFE train/val/test splits to ./{OUT_DIR}/")
    print(f"  Train: {X_train.shape}, Val: {X_val.shape}, Test: {X_test.shape}")


if __name__ == "__main__":
    main()

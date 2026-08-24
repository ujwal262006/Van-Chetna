"""
05b_extract_yamnet_frames.py

Upgrade over 05_extract_yamnet_embeddings.py: instead of collapsing each
clip's YAMNet frame embeddings into one mean-pooled vector (losing WHEN
things happen in the sound), this keeps the full frame sequence so a BiLSTM
can learn temporal patterns -- e.g. a chainsaw's startup whine vs. steady
cutting vs. idle, which averaging throws away.

Also adds waveform augmentation (time-shift, gain jitter, background noise
mixing) applied to TRAIN clips only, to manufacture more effective diversity
from FSC22's small size -- this is the other lever the published FSC22
research paper flagged as significantly impacting accuracy.

Run: python 05b_extract_yamnet_frames.py
"""

import os
import re
import glob
import numpy as np
import pandas as pd
import librosa
import tensorflow as tf
import tensorflow_hub as hub
from sklearn.model_selection import StratifiedGroupKFold

from importlib.util import spec_from_file_location, module_from_spec

def _load_mapping_module():
    spec = spec_from_file_location("label_mapping", os.path.join(os.path.dirname(__file__), "02_build_label_mapping.py"))
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

label_mod = _load_mapping_module()

# ---- EDIT THESE to match your actual paths (same as before) ----
AUDIO_DIR = "fsc22_data/Audio Wise V1.0-20220916T202003Z-001/Audio Wise V1.0"
METADATA_CSV = "fsc22_data/Metadata-20220916T202011Z-001/Metadata/Metadata V1.0 FSC22.csv"
OUT_DIR = "features_yamnet_frames"
YAMNET_SR = 16000
MAX_FRAMES = 12          # a 5s clip yields ~10 YAMNet frames; 12 gives headroom, pad shorter ones with zeros
AUGMENTATIONS_PER_TRAIN_CLIP = 2   # each train clip also gets this many augmented copies
# --------------------------------------------------------------------------------

YAMNET_URL = "https://tfhub.dev/google/yamnet/1"


def base_source_id(source_filename: str) -> str:
    m = re.sub(r'_+[A-Za-z]\.wav$', '', source_filename)
    return m if m != source_filename else source_filename.replace(".wav", "")


def augment_waveform(y, sr, rng):
    """Light, label-preserving augmentation: time shift, gain jitter, noise.
    Deliberately mild -- aggressive augmentation can change what a sound IS
    (e.g. too much pitch shift on a chainsaw could make it sound like
    something else), so we stick to transformations that don't change the
    semantic class."""
    y = y.copy()

    # Random time shift (wrap-around), up to 0.3s
    shift = rng.integers(-int(0.3 * sr), int(0.3 * sr))
    y = np.roll(y, shift)

    # Random gain, +/- 6dB
    gain_db = rng.uniform(-6, 6)
    y = y * (10 ** (gain_db / 20))

    # Light background noise
    noise_level = rng.uniform(0.001, 0.01)
    y = y + rng.normal(0, noise_level, size=y.shape).astype(np.float32)

    return np.clip(y, -1.0, 1.0).astype(np.float32)


def get_frame_embeddings(model, y):
    """Returns (n_frames, 1024) YAMNet embeddings, padded/truncated to MAX_FRAMES."""
    _, embeddings, _ = model(y)
    emb = embeddings.numpy()  # (n_frames_actual, 1024)
    n = emb.shape[0]
    if n >= MAX_FRAMES:
        return emb[:MAX_FRAMES]
    else:
        pad = np.zeros((MAX_FRAMES - n, emb.shape[1]), dtype=np.float32)
        return np.concatenate([emb, pad], axis=0)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    rng = np.random.default_rng(42)

    print("Loading YAMNet...")
    yamnet = hub.load(YAMNET_URL)

    meta = pd.read_csv(METADATA_CSV)
    id_to_label = label_mod.build_mapping_from_metadata(meta)

    name_col_candidates = [c for c in meta.columns if "dataset" in c.lower() and "file" in c.lower()]
    src_col_candidates = [c for c in meta.columns if "source" in c.lower() and "file" in c.lower()]
    dataset_col, source_col = name_col_candidates[0], src_col_candidates[0]

    filename_to_group = {}
    for _, row in meta.iterrows():
        filename_to_group[str(row[dataset_col])] = base_source_id(str(row[source_col]))

    files = sorted(glob.glob(os.path.join(AUDIO_DIR, "*.wav")))
    print(f"Found {len(files)} audio files.")

    # First pass: load raw waveforms + labels + groups (needed before we know
    # the split, since augmentation should only apply to whatever ends up in TRAIN)
    raw_data = []
    for f in files:
        fname = os.path.basename(f)
        class_id = fname.split("_")[0]
        label = id_to_label.get(class_id, "UNMAPPED")
        group = filename_to_group.get(fname)
        if label == "UNMAPPED" or group is None:
            continue
        try:
            y, _ = librosa.load(f, sr=YAMNET_SR, mono=True)
        except Exception as e:
            print(f"  Skipping {f}: {e}")
            continue
        raw_data.append({"y": y.astype(np.float32), "label": label, "group": group})

    print(f"Loaded {len(raw_data)} clips.")

    classes = sorted(set(d["label"] for d in raw_data))
    label_to_idx = {c: i for i, c in enumerate(classes)}
    y_all = np.array([label_to_idx[d["label"]] for d in raw_data])
    groups_all = np.array([d["group"] for d in raw_data])

    sgkf = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
    folds = list(sgkf.split(np.zeros(len(raw_data)), y_all, groups_all))
    test_idx = set(folds[0][1])
    val_idx = set(folds[1][1])
    train_idx = set(range(len(raw_data))) - test_idx - val_idx

    g_train = set(groups_all[i] for i in train_idx)
    g_val = set(groups_all[i] for i in val_idx)
    g_test = set(groups_all[i] for i in test_idx)
    assert not ((g_train & g_val) | (g_train & g_test) | (g_val & g_test)), "LEAKAGE detected"
    print("Verified: no source recording spans multiple splits.")

    def build_split(indices, augment):
        X, Y = [], []
        for i in sorted(indices):
            d = raw_data[i]
            X.append(get_frame_embeddings(yamnet, d["y"]))
            Y.append(label_to_idx[d["label"]])
            if augment:
                for _ in range(AUGMENTATIONS_PER_TRAIN_CLIP):
                    aug_y = augment_waveform(d["y"], YAMNET_SR, rng)
                    X.append(get_frame_embeddings(yamnet, aug_y))
                    Y.append(label_to_idx[d["label"]])
        return np.stack(X), np.array(Y)

    print("\nExtracting TRAIN embeddings (with augmentation)...")
    X_train, y_train = build_split(train_idx, augment=True)
    print("Extracting VAL embeddings (no augmentation)...")
    X_val, y_val = build_split(val_idx, augment=False)
    print("Extracting TEST embeddings (no augmentation)...")
    X_test, y_test = build_split(test_idx, augment=False)

    print(f"\nTrain: {X_train.shape} (includes augmented copies)")
    print(f"Val: {X_val.shape}, Test: {X_test.shape}")

    print("\nClass distribution (train, including augmented copies):")
    for c in classes:
        ci = label_to_idx[c]
        print(f"  {c}: {sum(y_train==ci)}")

    np.save(os.path.join(OUT_DIR, "X_train.npy"), X_train)
    np.save(os.path.join(OUT_DIR, "y_train.npy"), y_train)
    np.save(os.path.join(OUT_DIR, "X_val.npy"), X_val)
    np.save(os.path.join(OUT_DIR, "y_val.npy"), y_val)
    np.save(os.path.join(OUT_DIR, "X_test.npy"), X_test)
    np.save(os.path.join(OUT_DIR, "y_test.npy"), y_test)
    with open(os.path.join(OUT_DIR, "classes.txt"), "w") as fh:
        fh.write("\n".join(classes))

    print(f"\nSaved frame-level embeddings to ./{OUT_DIR}/")


if __name__ == "__main__":
    main()

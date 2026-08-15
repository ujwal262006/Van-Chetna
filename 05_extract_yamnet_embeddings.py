"""
05_extract_yamnet_embeddings.py

Switches from "train a CNN from scratch on spectrograms" to "use a pretrained
audio model (YAMNet) as a feature extractor, train a small classifier on top."

Why: your last two runs (from-scratch CNN, with and without augmentation)
plateaued at 21-31% test accuracy on ~1200 training clips. That's not a bug in
your code -- it's the expected outcome of training a CNN from raw audio
features on this little data. Published FSC22 research (MobileNet/GoogleNet/
ResNet + BiLSTM) validates the same conclusion: pretrained-feature-extractor
approaches meaningfully outperform from-scratch training on this dataset.

YAMNet is Google's audio event model, pretrained on AudioSet (2M+ clips,
521 classes) -- exactly the kind of general "what does this sound like"
knowledge a from-scratch CNN can't get from 1200 forest clips alone.

What this does:
  1. Loads each clip, resamples to 16kHz mono (YAMNet's required input)
  2. Runs it through YAMNet -> get one 1024-dim embedding per ~0.96s frame
     (a 5s clip produces roughly 5 frames)
  3. Mean-pools across frames -> one 1024-dim embedding per clip
  4. Uses the SAME group-safe (no source-recording leakage) split logic as
     03_extract_features_v2.py
  5. Saves embeddings as .npy, ready for a small classifier (06_train_yamnet_classifier.py)

First run will download YAMNet (~15MB) from TensorFlow Hub -- needs internet.

Run: pip install tensorflow tensorflow-hub
     python 05_extract_yamnet_embeddings.py
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

# ---- EDIT THESE to match your actual paths (same as 03_extract_features_v2.py) ----
AUDIO_DIR = "fsc22_data/Audio Wise V1.0-20220916T202003Z-001/Audio Wise V1.0"
METADATA_CSV = "fsc22_data/Metadata-20220916T202011Z-001/Metadata/Metadata V1.0 FSC22.csv"
OUT_DIR = "features_yamnet"
YAMNET_SR = 16000
# --------------------------------------------------------------------------------

YAMNET_URL = "https://tfhub.dev/google/yamnet/1"


def base_source_id(source_filename: str) -> str:
    m = re.sub(r'_+[A-Za-z]\.wav$', '', source_filename)
    return m if m != source_filename else source_filename.replace(".wav", "")


def get_yamnet_embedding(model, filepath):
    y, sr = librosa.load(filepath, sr=YAMNET_SR, mono=True)
    y = y.astype(np.float32)
    # YAMNet expects a 1-D float32 waveform in [-1, 1] at 16kHz
    _, embeddings, _ = model(y)          # embeddings: (n_frames, 1024)
    return embeddings.numpy().mean(axis=0)  # mean-pool over time -> (1024,)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    print("Loading YAMNet from TensorFlow Hub (downloads ~15MB on first run)...")
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
    print(f"Found {len(files)} audio files. Extracting YAMNet embeddings (this takes a few minutes on CPU)...")

    X, y_labels, groups, skipped = [], [], [], 0
    for i, f in enumerate(files):
        fname = os.path.basename(f)
        class_id = fname.split("_")[0]
        label = id_to_label.get(class_id, "UNMAPPED")
        group = filename_to_group.get(fname)
        if label == "UNMAPPED" or group is None:
            skipped += 1
            continue
        try:
            emb = get_yamnet_embedding(yamnet, f)
        except Exception as e:
            print(f"  Skipping {f}: {e}")
            skipped += 1
            continue
        X.append(emb)
        y_labels.append(label)
        groups.append(group)
        if (i + 1) % 200 == 0:
            print(f"  Processed {i + 1}/{len(files)}...")

    print(f"\nExtracted embeddings for {len(X)} clips, skipped {skipped}.")

    X = np.stack(X)  # (N, 1024)
    classes = sorted(set(y_labels))
    label_to_idx = {c: i for i, c in enumerate(classes)}
    y = np.array([label_to_idx[l] for l in y_labels])
    groups = np.array(groups)

    print(f"Unique source recordings (groups): {len(set(groups))} out of {len(X)} clips")

    sgkf = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
    folds = list(sgkf.split(X, y, groups))
    test_idx = folds[0][1]
    val_idx = folds[1][1]
    train_idx = np.array(sorted(set(range(len(X))) - set(test_idx) - set(val_idx)))

    X_train, y_train = X[train_idx], y[train_idx]
    X_val, y_val = X[val_idx], y[val_idx]
    X_test, y_test = X[test_idx], y[test_idx]

    g_train, g_val, g_test = set(groups[train_idx]), set(groups[val_idx]), set(groups[test_idx])
    overlap = (g_train & g_val) | (g_train & g_test) | (g_val & g_test)
    assert not overlap, f"LEAKAGE: {overlap}"
    print("Verified: no source recording spans multiple splits.")

    print("\nClass distribution (train / val / test):")
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

    print(f"\nSaved YAMNet-embedding train/val/test splits to ./{OUT_DIR}/")
    print(f"  Train: {X_train.shape}, Val: {X_val.shape}, Test: {X_test.shape}")


if __name__ == "__main__":
    main()

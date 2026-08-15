"""
03_extract_features.py

Converts every FSC22 clip into a log-mel spectrogram, applies the simplified
label mapping from 02_build_label_mapping.py, and saves a stratified
train/val/test split ready for CNN training (matches the pipeline described
in the Forest Guard plan, Section 13: 16kHz, 40 mel bands, 1024-pt FFT).
"""

import os
import glob
import numpy as np
import pandas as pd
import librosa
from sklearn.model_selection import train_test_split

from importlib.util import spec_from_file_location, module_from_spec

def _load_mapping_module():
    spec = spec_from_file_location("label_mapping", os.path.join(os.path.dirname(__file__), "02_build_label_mapping.py"))
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

label_mod = _load_mapping_module()

# ---- EDIT THESE ----
AUDIO_DIR = "fsc22_data/Audio Wise V1.0-20220916T202003Z-001/Audio Wise V1.0" 
METADATA_CSV = "fsc22_data/Metadata-20220916T202011Z-001/Metadata/Metadata V1.0 FSC22.csv"
OUT_DIR = "features"
SAMPLE_RATE = 16000       # per Forest Guard acoustic pipeline spec
N_MELS = 40
N_FFT = 1024
HOP_LENGTH = 512
CLIP_DURATION_SEC = 5     # FSC22 clips are already 5s
# ----------------------

TARGET_LEN = SAMPLE_RATE * CLIP_DURATION_SEC


def extract_log_mel(filepath):
    y, sr = librosa.load(filepath, sr=SAMPLE_RATE)
    # pad/truncate to a fixed length so all feature arrays are the same shape
    if len(y) < TARGET_LEN:
        y = np.pad(y, (0, TARGET_LEN - len(y)))
    else:
        y = y[:TARGET_LEN]
    mel = librosa.feature.melspectrogram(
        y=y, sr=SAMPLE_RATE, n_mels=N_MELS, n_fft=N_FFT, hop_length=HOP_LENGTH
    )
    log_mel = librosa.power_to_db(mel, ref=np.max)
    return log_mel.astype(np.float32)  # shape: (N_MELS, time_frames)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    meta = pd.read_csv(METADATA_CSV)
    id_to_label = label_mod.build_mapping_from_metadata(meta)

    files = glob.glob(os.path.join(AUDIO_DIR, "*.wav"))
    print(f"Found {len(files)} audio files.")

    X, y_labels, skipped = [], [], 0
    for f in files:
        class_id = os.path.basename(f).split("_")[0]
        label = id_to_label.get(class_id, "UNMAPPED")
        if label == "UNMAPPED":
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

    print(f"Extracted features for {len(X)} clips, skipped {skipped} (unmapped or unreadable).")
    if skipped > 0:
        print("Fix unmapped classes in 02_build_label_mapping.py before proceeding — you are")
        print("currently throwing away real training data.")

    X = np.stack(X)                      # (N, N_MELS, time_frames)
    classes = sorted(set(y_labels))
    label_to_idx = {c: i for i, c in enumerate(classes)}
    y = np.array([label_to_idx[l] for l in y_labels])

    print("\nSimplified class distribution:")
    for c in classes:
        print(f"  {c}: {sum(1 for l in y_labels if l == c)} samples")

    # 70/15/15 stratified split per the Forest Guard AI spec (Section 11)
    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=0.30, random_state=42, stratify=y
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.50, random_state=42, stratify=y_temp
    )

    np.save(os.path.join(OUT_DIR, "X_train.npy"), X_train)
    np.save(os.path.join(OUT_DIR, "y_train.npy"), y_train)
    np.save(os.path.join(OUT_DIR, "X_val.npy"), X_val)
    np.save(os.path.join(OUT_DIR, "y_val.npy"), y_val)
    np.save(os.path.join(OUT_DIR, "X_test.npy"), X_test)
    np.save(os.path.join(OUT_DIR, "y_test.npy"), y_test)
    with open(os.path.join(OUT_DIR, "classes.txt"), "w") as fh:
        fh.write("\n".join(classes))

    print(f"\nSaved train/val/test splits to ./{OUT_DIR}/")
    print(f"  Train: {X_train.shape}, Val: {X_val.shape}, Test: {X_test.shape}")
    print(f"  Classes ({len(classes)}): {classes}")


if __name__ == "__main__":
    main()

"""
01_explore_dataset.py
Explore the real FSC22 dataset structure before writing any model code.

Run this AFTER downloading + unzipping the dataset per 00_SETUP_GUIDE.md.
Adjust AUDIO_DIR / METADATA_CSV below to match your actual unzipped folder names.
"""

import os
import glob
import pandas as pd
import matplotlib.pyplot as plt
import librosa
import librosa.display

# ---- EDIT THESE TO MATCH YOUR ACTUAL DOWNLOADED FOLDER ----
AUDIO_DIR = "fsc22_data/Audio Wise V1.0-20220916T202003Z-001/Audio Wise V1.0"          # folder containing the .wav files
METADATA_CSV = "fsc22_data/Metadata-20220916T202011Z-001/Metadata/Metadata V1.0 FSC22.csv"  # the Class ID -> Class Name CSV
# -------------------------------------------------------------

def load_metadata(csv_path):
    if not os.path.exists(csv_path):
        raise FileNotFoundError(
            f"Metadata CSV not found at {csv_path}. "
            f"Run `find fsc22_data -iname '*.csv'` and update METADATA_CSV above."
        )
    df = pd.read_csv(csv_path)
    print("Metadata columns found:", list(df.columns))
    print(df.head(10))
    return df

def class_distribution(audio_dir):
    """Count clips per Class ID directly from filenames: ClassID_AudioID.wav"""
    files = glob.glob(os.path.join(audio_dir, "*.wav"))
    print(f"\nTotal audio files found: {len(files)} (expected 2025)")
    counts = {}
    for f in files:
        class_id = os.path.basename(f).split("_")[0]
        counts[class_id] = counts.get(class_id, 0) + 1
    print(f"Distinct class IDs found: {len(counts)} (expected 27)")
    for cid in sorted(counts, key=lambda x: int(x)):
        print(f"  Class {cid}: {counts[cid]} clips")
    return counts, files

def plot_sample(filepath, title):
    y, sr = librosa.load(filepath, sr=None)
    fig, axes = plt.subplots(2, 1, figsize=(8, 5))

    librosa.display.waveshow(y, sr=sr, ax=axes[0])
    axes[0].set_title(f"Waveform — {title}")

    mel = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=40)
    mel_db = librosa.power_to_db(mel, ref=1.0)
    img = librosa.display.specshow(mel_db, sr=sr, x_axis="time", y_axis="mel", ax=axes[1])
    axes[1].set_title(f"Log-Mel Spectrogram — {title}")
    fig.colorbar(img, ax=axes[1], format="%+2.0f dB")

    fig.tight_layout()
    out_name = f"sample_{title.replace(' ', '_')}.png"
    fig.savefig(out_name, dpi=120)
    print(f"Saved plot: {out_name}")
    plt.close(fig)

if __name__ == "__main__":
    meta = load_metadata(METADATA_CSV)
    counts, files = class_distribution(AUDIO_DIR)

    # Plot one example per a handful of class IDs so you can SEE what you're working with.
    # Adjust these IDs once you know from the metadata CSV which IDs are Chainsaw/Axe/etc.
    sample_class_ids = ["1", "5", "10", "15", "20", "25"]
    for cid in sample_class_ids:
        matches = [f for f in files if os.path.basename(f).startswith(f"{cid}_")]
        if matches:
            plot_sample(matches[0], f"Class{cid}")
        else:
            print(f"No files found for class id {cid} — check your class ID range (should be 1-27).")

    print("\nDone. Cross-reference the printed metadata table with the class IDs above")
    print("to know exactly which sounds you just plotted, then fill in 02_build_label_mapping.py.")

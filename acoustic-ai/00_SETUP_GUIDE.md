# FSC22 — Getting Started Guide (Day 1 task)

FSC22 lives on Kaggle: https://www.kaggle.com/datasets/irmiot22/fsc22-dataset
(also mirrored on IEEE DataPort). Confirmed real specs:

- **2,025 audio clips**, **27 classes**, **75 clips per class**
- Each clip is **5 seconds**, **44.1 kHz**, **WAV**
- 6 parent categories: Mechanical, Animal, Environmental, Vehicle, Forest Threat, Human
- Filenames: `ClassID_UniqueAudioID.wav` (e.g. `1_10101.wav`), Class ID from 1–27
- Ships with a **Metadata folder** containing a CSV mapping Class ID → Class Name — this
  is the source of truth for exact class names; don't hardcode guessed names.

## Step 1 — Get a Kaggle API token (5 minutes)

1. Go to kaggle.com → Account → "Create New API Token" → downloads `kaggle.json`
2. On your machine:
   ```bash
   mkdir -p ~/.kaggle
   mv ~/Downloads/kaggle.json ~/.kaggle/kaggle.json
   chmod 600 ~/.kaggle/kaggle.json
   pip install kaggle
   ```

## Step 2 — Download the dataset

```bash
kaggle datasets download -d irmiot22/fsc22-dataset
unzip fsc22-dataset.zip -d fsc22_data
```

You should end up with something like:
```
fsc22_data/
  Audio Wise V1.0-20220916T145035Z-001/   (folder name may vary by version)
    Audios/
      1_10101.wav
      1_10102.wav
      ...
      27_xxxxx.wav
  Metadata V1.0-...csv   (Class ID -> Class Name mapping)
```
If the exact folder/file names differ slightly (Kaggle versions have shuffled this
before), run `find fsc22_data -maxdepth 3` and adjust the `AUDIO_DIR` / `METADATA_CSV`
paths at the top of `01_explore_dataset.py` accordingly — don't assume, check.

## Step 3 — Environment

```bash
pip install librosa soundfile numpy pandas matplotlib scikit-learn tensorflow
```
(`tensorflow` only needed once you get to model training in a later step — skip it
for just exploring/preprocessing.)

## Step 4 — Run the starter scripts, in order

1. `01_explore_dataset.py` — loads the real metadata CSV, prints class distribution,
   plots a waveform + mel-spectrogram for one sample per parent category so you can
   *see* what you're working with before writing any model code.
2. `02_build_label_mapping.py` — maps the 27 fine-grained FSC22 classes down to the
   5–6 simplified threat classes Forest Guard actually needs
   (Normal / Chainsaw-Threat / Human / Vehicle / Animal / Environmental).
   **You must open this file and fill in the mapping using the real class names
   printed by script 01** — a placeholder mapping is included based on commonly
   documented FSC22 classes (axe, chainsaw, handsaw, generator, fire, rain, wind,
   thunderstorm, etc.) but verify every name against your actual metadata CSV before
   trusting it, since class-name spelling has varied slightly across dataset versions.
3. `03_extract_features.py` — converts every clip to a log-mel spectrogram, applies
   the simplified label mapping, and saves a train/val/test split as `.npy` files
   ready for CNN training.

## What "done" looks like for Day 1–3

By the end of Day 3 in the 10-day plan you should have:
- `features_train.npy`, `features_val.npy`, `features_test.npy` (+ matching label arrays)
- A printed class-distribution table showing how many samples land in each of your
  5–6 simplified classes (expect this to be imbalanced — "Normal/Environmental" will
  have far more source classes folded into it than "Chainsaw")
- A first baseline CNN training run (even a rough one) — that's a separate script
  once features are ready; ping me when you're at that point and I'll build it with
  you against your actual class balance numbers.

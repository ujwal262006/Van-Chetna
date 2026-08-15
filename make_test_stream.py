import os
import glob
import librosa
import soundfile as sf
import numpy as np

AUDIO_DIR = r"fsc22_data\Audio Wise V1.0-20220916T202003Z-001\Audio Wise V1.0"
OUTPUT = "test_stream.wav"

# One real FSC22 class from each of these IDs:
# 1 Fire
# 7 TreeFalling
# 8 Helicopter
# 11 Chainsaw
# 18 Speaking
# 22 Frog

class_ids = ["1", "7", "8", "11", "18", "22"]

all_files = glob.glob(os.path.join(AUDIO_DIR, "*.wav"))

selected = []

for class_id in class_ids:
    matches = [
        f for f in all_files
        if os.path.basename(f).startswith(class_id + "_")
    ]

    if not matches:
        print(f"WARNING: No file found for class {class_id}")
        continue

    selected.append(sorted(matches)[0])

print("Selected files:")
for f in selected:
    print(" ", os.path.basename(f))

audio = []

for file in selected:
    y, sr = librosa.load(file, sr=16000, mono=True)
    audio.append(y)

combined = np.concatenate(audio)

sf.write(OUTPUT, combined, 16000)

print()
print(f"Created: {OUTPUT}")
print(f"Duration: {len(combined) / 16000:.2f} seconds")
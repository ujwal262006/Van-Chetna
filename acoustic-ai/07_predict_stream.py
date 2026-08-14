"""
07_predict_stream.py

Turns the trained YAMNet + classifier into something that behaves like the
real acoustic pipeline from the Forest Guard architecture doc (Section 13):
sliding windows over continuous audio, per-window classification, a
confidence threshold, and temporal smoothing (require 2 consecutive windows
above threshold before raising an event) to cut false positives.

This is what your ESP32 gateway logic should mirror -- test it here on a
longer audio file first (record a few minutes of mixed sounds, or concatenate
a few FSC22 clips) before wiring it to the real microphone.

Run: python 07_predict_stream.py path/to/some_longer_audio.wav
"""

import sys
import os
import json
import numpy as np
import librosa
import tensorflow as tf
import tensorflow_hub as hub
from datetime import datetime, timezone

MODEL_PATH = "models/best_model_yamnet.keras"   # or final_model_yamnet.keras
CLASSES_PATH = "features_yamnet/classes.txt"
YAMNET_URL = "https://tfhub.dev/google/yamnet/1"
SAMPLE_RATE = 16000

WINDOW_SEC = 5.0          # matches FSC22 clip length / Section 13 spec
HOP_SEC = 2.5             # 50% overlap, per Section 13
CONFIDENCE_THRESHOLD = 0.7
CONSECUTIVE_WINDOWS_REQUIRED = 2   # temporal smoothing: cuts one-off false positives

# Classes that count as a "threat" worth raising an alert for.
# Adjust based on your final class set (e.g. if you merged Generator_Mechanical
# into Chainsaw_Threat, this list stays the same).
THREAT_CLASSES = {"Chainsaw_Threat", "Fire_Threat", "Vehicle"}


def load_classes():
    with open(CLASSES_PATH) as f:
        return [line.strip() for line in f if line.strip()]


def sliding_windows(y, sr, window_sec, hop_sec):
    window_len = int(window_sec * sr)
    hop_len = int(hop_sec * sr)
    start = 0
    while start + window_len <= len(y):
        yield start / sr, y[start:start + window_len]
        start += hop_len
    # tail window, if any meaningful audio remains
    if start < len(y) and (len(y) - start) > window_len * 0.5:
        remainder = y[start:]
        padded = np.pad(remainder, (0, window_len - len(remainder)))
        yield start / sr, padded


def main():
    if len(sys.argv) < 2:
        print("Usage: python 07_predict_stream.py path/to/audio.wav")
        sys.exit(1)
    audio_path = sys.argv[1]

    classes = load_classes()
    print(f"Loaded classes: {classes}")

    print("Loading YAMNet...")
    yamnet = hub.load(YAMNET_URL)

    print(f"Loading classifier from {MODEL_PATH}...")
    classifier = tf.keras.models.load_model(MODEL_PATH)

    print(f"Loading audio: {audio_path}")
    y, sr = librosa.load(audio_path, sr=SAMPLE_RATE, mono=True)
    duration = len(y) / sr
    print(f"Audio duration: {duration:.1f}s -- running {WINDOW_SEC}s windows, {HOP_SEC}s hop\n")

    consecutive_hits = {c: 0 for c in classes}
    events = []

    for t_start, window in sliding_windows(y, sr, WINDOW_SEC, HOP_SEC):
        _, embeddings, _ = yamnet(window.astype(np.float32))
        emb = embeddings.numpy().mean(axis=0, keepdims=True)  # (1, 1024)
        probs = classifier.predict(emb, verbose=0)[0]
        pred_idx = int(np.argmax(probs))
        pred_class = classes[pred_idx]
        confidence = float(probs[pred_idx])

        print(f"[t={t_start:5.1f}s] {pred_class:22s} confidence={confidence:.3f}")

        # temporal smoothing per class
        for c in classes:
            if c == pred_class and confidence >= CONFIDENCE_THRESHOLD:
                consecutive_hits[c] += 1
            else:
                consecutive_hits[c] = 0

        if (
            pred_class in THREAT_CLASSES
            and confidence >= CONFIDENCE_THRESHOLD
            and consecutive_hits[pred_class] >= CONSECUTIVE_WINDOWS_REQUIRED
        ):
            event = {
                "node_id": "NODE_01_TEST",
                "event_id": f"evt_{int(t_start*1000)}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "sensor_type": "acoustic",
                "class": pred_class.lower().replace("_threat", ""),
                "confidence": round(confidence, 3),
                "window_start_sec": round(t_start, 1),
            }
            events.append(event)
            print(f"  >>> THREAT EVENT (confirmed over {CONSECUTIVE_WINDOWS_REQUIRED} windows): {json.dumps(event)}")
            consecutive_hits[pred_class] = 0  # reset after firing, avoid duplicate spam

    print(f"\n{'='*60}")
    print(f"Total confirmed threat events: {len(events)}")
    if events:
        print("These are the exact JSON payloads your ESP32/gateway would send over LoRa")
        print("(per the LoRa payload format in the architecture doc, Section 16).")
    else:
        print("No threat events confirmed. If you expected some, try lowering")
        print(f"CONFIDENCE_THRESHOLD (currently {CONFIDENCE_THRESHOLD}) or check your test audio.")


if __name__ == "__main__":
    main()

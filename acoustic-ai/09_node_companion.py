"""
09_node_companion.py

Bridges Member 2's ESP32 (mic capture, buffered per-window over serial) to
your existing YAMNet + classifier pipeline (05/06/07), and sends confirmed
threat events back to the ESP32 over the same serial connection for LoRa
transmission.

WHY THIS EXISTS: continuously streaming raw 16kHz audio over standard serial
isn't feasible (32KB/s needed vs ~11.5KB/s available at 115200 baud). Instead,
the ESP32 buffers one 5-second window in RAM, sends it as ONE compact binary
chunk, then has the next 2.5s (hop overlap handled here, not on-chip) of
"quiet time" to fill the next buffer while this script classifies the
previous one. This matches the windowed pipeline you already built and
tested in 07_predict_stream.py -- no architecture change, just batching.

WIRE PROTOCOL (agree this with Member 2 before they build the real firmware):
  ESP32 -> laptop (one audio window):
    4 bytes:  magic header b"AUD1"
    4 bytes:  sample count, uint32 little-endian (expect 80000 for 5s @16kHz)
    N*2 bytes: raw int16 PCM samples, little-endian, mono

  laptop -> ESP32 (only sent when a threat is CONFIRMED, i.e. rarely):
    One line of JSON, newline-terminated, matching the exact schema
    lora_sender.ino already uses:
    {"node_id":"NODE_01","event_id":"evt_...","timestamp":"...",
     "sensor_type":"acoustic","class":"chainsaw","confidence":0.91,
     "battery_pct":<esp32 fills this in>,"lat":...,"lon":...}
    The ESP32 firmware should read this line and LoRa.print() it directly --
    same beginPacket/print/endPacket pattern already in lora_sender.ino,
    just with real data instead of the hardcoded test payload.

Run against real hardware:
    python 09_node_companion.py --port COM5

Run in self-test mode (no hardware needed, uses synthetic audio):
    python 09_node_companion.py --selftest
"""

import sys
import json
import struct
import argparse
import numpy as np
from datetime import datetime, timezone

MAGIC = b"AUD1"
SAMPLE_RATE = 16000
WINDOW_SAMPLES = SAMPLE_RATE * 5  # 5-second windows, matches your trained pipeline

CONFIDENCE_THRESHOLD = 0.7
CONSECUTIVE_WINDOWS_REQUIRED = 2
THREAT_CLASSES = {"Chainsaw_Threat", "Fire_Threat", "Vehicle"}

CLASSES_PATH = "features_yamnet/classes.txt"
MODEL_PATH = "models/best_model_yamnet.keras"
YAMNET_URL = "https://tfhub.dev/google/yamnet/1"

NODE_ID = "NODE_01"
NODE_LAT = 30.4520   # set to your actual demo location
NODE_LON = 77.5890


def load_classes():
    with open(CLASSES_PATH) as f:
        return [line.strip() for line in f if line.strip()]


def read_audio_window_from_serial(ser):
    """Reads one AUD1-framed window from an open pyserial connection.
    Returns a float32 numpy array in [-1, 1], or None on framing error."""
    header = ser.read(4)
    if header != MAGIC:
        # resync: not a real error necessarily, could be stray bytes/noise
        return None
    count_bytes = ser.read(4)
    if len(count_bytes) < 4:
        return None
    (sample_count,) = struct.unpack("<I", count_bytes)
    if sample_count <= 0 or sample_count > SAMPLE_RATE * 10:  # sanity bound
        print(f"  Rejecting implausible sample count: {sample_count}")
        return None
    raw = ser.read(sample_count * 2)
    if len(raw) < sample_count * 2:
        print("  Incomplete audio window (timeout or disconnect)")
        return None
    samples = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    return samples


def make_synthetic_window(rng):
    """For --selftest: generates a plausible-looking window so the
    classify+event logic can be verified without real hardware."""
    return (rng.standard_normal(WINDOW_SAMPLES) * 0.05).astype(np.float32)


def classify_window(yamnet, classifier, classes, audio):
    _, embeddings, _ = yamnet(audio)
    emb = embeddings.numpy().mean(axis=0, keepdims=True)
    probs = classifier.predict(emb, verbose=0)[0]
    idx = int(np.argmax(probs))
    return classes[idx], float(probs[idx])


def build_event_json(pred_class, confidence, battery_pct=100):
    return json.dumps({
        "node_id": NODE_ID,
        "event_id": f"evt_{int(datetime.now(timezone.utc).timestamp()*1000)}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sensor_type": "acoustic",
        "class": pred_class.lower().replace("_threat", ""),
        "confidence": round(confidence, 3),
        "battery_pct": battery_pct,
        "lat": NODE_LAT,
        "lon": NODE_LON,
    })


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", help="Serial port, e.g. COM5")
    parser.add_argument("--baud", type=int, default=921600,
                         help="Must match ESP32 firmware's Serial.begin() rate")
    parser.add_argument("--selftest", action="store_true",
                         help="Run without hardware using synthetic audio")
    args = parser.parse_args()

    if not args.selftest and not args.port:
        print("Provide --port COM5 (or similar) or use --selftest")
        sys.exit(1)

    print("Loading classifier + YAMNet (same as 06/07)...")
    import tensorflow as tf
    import tensorflow_hub as hub
    classes = load_classes()
    yamnet = hub.load(YAMNET_URL)
    classifier = tf.keras.models.load_model(MODEL_PATH)
    print(f"Ready. Classes: {classes}")

    consecutive_hits = {c: 0 for c in classes}

    if args.selftest:
        print("\n--selftest mode: generating synthetic windows, no serial hardware needed\n")
        rng = np.random.default_rng(0)
        for i in range(5):
            audio = make_synthetic_window(rng)
            pred_class, confidence = classify_window(yamnet, classifier, classes, audio)
            print(f"[window {i}] {pred_class} confidence={confidence:.3f}")
            for c in classes:
                if c == pred_class and confidence >= CONFIDENCE_THRESHOLD:
                    consecutive_hits[c] += 1
                else:
                    consecutive_hits[c] = 0
            if (pred_class in THREAT_CLASSES and confidence >= CONFIDENCE_THRESHOLD
                    and consecutive_hits[pred_class] >= CONSECUTIVE_WINDOWS_REQUIRED):
                event = build_event_json(pred_class, confidence)
                print(f"  >>> WOULD SEND TO ESP32 OVER SERIAL: {event}")
                consecutive_hits[pred_class] = 0
        print("\nSelf-test complete. Synthetic noise won't reliably trigger events -- ")
        print("that's expected. This just verifies the classify+event logic runs end to end.")
        return

    import serial
    print(f"Opening {args.port} at {args.baud} baud...")
    ser = serial.Serial(args.port, args.baud, timeout=5)

    print("Listening for audio windows from ESP32...")
    while True:
        audio = read_audio_window_from_serial(ser)
        if audio is None:
            continue
        pred_class, confidence = classify_window(yamnet, classifier, classes, audio)
        print(f"{pred_class:22s} confidence={confidence:.3f}")

        for c in classes:
            if c == pred_class and confidence >= CONFIDENCE_THRESHOLD:
                consecutive_hits[c] += 1
            else:
                consecutive_hits[c] = 0

        if (pred_class in THREAT_CLASSES and confidence >= CONFIDENCE_THRESHOLD
                and consecutive_hits[pred_class] >= CONSECUTIVE_WINDOWS_REQUIRED):
            event = build_event_json(pred_class, confidence)
            ser.write((event + "\n").encode("utf-8"))
            print(f"  >>> SENT TO ESP32 FOR LoRa: {event}")
            consecutive_hits[pred_class] = 0


if __name__ == "__main__":
    main()

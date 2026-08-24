"""
11_ensemble_eval.py

Combines predictions from your two trained models (06's mean-pooled Dense
classifier, 83.21%, and 06b's BiLSTM on frame sequences, 84.69%) by
averaging their softmax probabilities. Since they see the same audio
differently (static summary vs. temporal sequence), they tend to make
different mistakes -- ensembling often recovers a few points for free, with
zero additional training.

This does NOT retrain anything -- it's a quick, low-risk experiment to run
before concluding what your final model / final accuracy number is.

Run: python 11_ensemble_eval.py
"""

import numpy as np
import tensorflow as tf
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import matplotlib.pyplot as plt

DENSE_MODEL_PATH = "models/best_model_yamnet.keras"
BILSTM_MODEL_PATH = "models/best_model_bilstm.keras"

DENSE_FEATURES_DIR = "features_yamnet"
FRAME_FEATURES_DIR = "features_yamnet_frames"


def load_classes(path):
    with open(path) as f:
        return [line.strip() for line in f if line.strip()]


def main():
    classes_dense = load_classes(f"{DENSE_FEATURES_DIR}/classes.txt")
    classes_frame = load_classes(f"{FRAME_FEATURES_DIR}/classes.txt")
    assert classes_dense == classes_frame, (
        f"Class lists don't match between the two feature sets! "
        f"{classes_dense} vs {classes_frame} -- did you re-run 02_build_label_mapping.py "
        f"differently between the two extraction runs? Ensembling isn't valid if so."
    )
    classes = classes_dense
    print(f"Classes: {classes}")

    y_test_dense = np.load(f"{DENSE_FEATURES_DIR}/y_test.npy")
    y_test_frame = np.load(f"{FRAME_FEATURES_DIR}/y_test.npy")

    # Critical sanity check: the two test sets must be the SAME clips in the
    # SAME order for index-aligned ensembling to be valid. Both scripts use
    # the same group-safe split logic with the same random seed, so this
    # SHOULD match -- but verify rather than assume.
    if not np.array_equal(y_test_dense, y_test_frame):
        print("\n*** WARNING: y_test arrays don't match between the two feature sets! ***")
        print("This means the test splits are NOT the same clips in the same order.")
        print("Ensembling by index would silently combine predictions for DIFFERENT")
        print("audio clips, producing meaningless results. Stopping here.")
        print("Most likely cause: 02_build_label_mapping.py changed between when")
        print("05_extract_yamnet_embeddings.py and 05b_extract_yamnet_frames.py were run.")
        return
    print(f"Verified: test sets are aligned ({len(y_test_dense)} matching clips).\n")

    y_test = y_test_dense

    print("Loading models...")
    dense_model = tf.keras.models.load_model(DENSE_MODEL_PATH)
    bilstm_model = tf.keras.models.load_model(BILSTM_MODEL_PATH)

    X_test_dense = np.load(f"{DENSE_FEATURES_DIR}/X_test.npy")
    X_test_frame = np.load(f"{FRAME_FEATURES_DIR}/X_test.npy")

    print("Getting predictions from both models...")
    probs_dense = dense_model.predict(X_test_dense, verbose=0)
    probs_bilstm = bilstm_model.predict(X_test_frame, verbose=0)

    pred_dense = np.argmax(probs_dense, axis=1)
    pred_bilstm = np.argmax(probs_bilstm, axis=1)

    acc_dense = accuracy_score(y_test, pred_dense)
    acc_bilstm = accuracy_score(y_test, pred_bilstm)
    print(f"\nDense model solo accuracy on this test set:  {acc_dense:.4f}")
    print(f"BiLSTM model solo accuracy on this test set: {acc_bilstm:.4f}")

    # Simple average ensemble
    probs_ensemble = (probs_dense + probs_bilstm) / 2.0
    pred_ensemble = np.argmax(probs_ensemble, axis=1)
    acc_ensemble = accuracy_score(y_test, pred_ensemble)
    print(f"\nENSEMBLE (average) accuracy: {acc_ensemble:.4f}")

    if acc_ensemble > max(acc_dense, acc_bilstm):
        print(f"  -> Ensembling HELPED: +{(acc_ensemble - max(acc_dense, acc_bilstm))*100:.2f} points over the better solo model")
    else:
        print(f"  -> Ensembling did NOT help here -- stick with the better solo model ({'BiLSTM' if acc_bilstm > acc_dense else 'Dense'})")

    print("\nClassification report (ensemble):")
    print(classification_report(y_test, pred_ensemble, target_names=classes, digits=3, zero_division=0))

    # Also try weighting the better model more heavily (60/40), since a
    # simple 50/50 average isn't always optimal
    for w_bilstm in [0.6, 0.7]:
        w_dense = 1 - w_bilstm
        probs_weighted = w_dense * probs_dense + w_bilstm * probs_bilstm
        pred_weighted = np.argmax(probs_weighted, axis=1)
        acc_weighted = accuracy_score(y_test, pred_weighted)
        print(f"Weighted ensemble ({int(w_dense*100)}% Dense / {int(w_bilstm*100)}% BiLSTM): {acc_weighted:.4f}")

    cm = confusion_matrix(y_test, pred_ensemble)
    fig, ax = plt.subplots(figsize=(7, 6))
    im = ax.imshow(cm, cmap="Greens")
    ax.set_xticks(range(len(classes))); ax.set_yticks(range(len(classes)))
    ax.set_xticklabels(classes, rotation=45, ha="right")
    ax.set_yticklabels(classes)
    ax.set_xlabel("Predicted"); ax.set_ylabel("True")
    ax.set_title(f"Confusion Matrix — Ensemble (acc={acc_ensemble:.3f})")
    for i in range(len(classes)):
        for j in range(len(classes)):
            ax.text(j, i, cm[i, j], ha="center", va="center",
                     color="white" if cm[i, j] > cm.max() / 2 else "black")
    fig.colorbar(im, ax=ax)
    fig.tight_layout()
    fig.savefig("models/confusion_matrix_ensemble.png", dpi=120)
    print("\nSaved models/confusion_matrix_ensemble.png")


if __name__ == "__main__":
    main()
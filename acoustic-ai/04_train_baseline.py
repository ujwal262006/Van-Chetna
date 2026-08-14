"""
04_train_baseline.py

Trains a small CNN on the log-mel features extracted in 03_extract_features.py.
Handles the real class imbalance in your data (Generator_Mechanical: 75 samples
vs Animal: 525) using class weighting rather than ignoring it.

Run: python 04_train_baseline.py
Requires: tensorflow (pip install tensorflow)
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from sklearn.utils.class_weight import compute_class_weight
from sklearn.metrics import classification_report, confusion_matrix
import tensorflow as tf
from tensorflow.keras import layers, models, callbacks

FEATURES_DIR = "features"
OUT_DIR = "models"
os.makedirs(OUT_DIR, exist_ok=True)

BATCH_SIZE = 32
EPOCHS = 50          # early stopping will likely cut this short
LEARNING_RATE = 1e-3


def load_split(name):
    X = np.load(os.path.join(FEATURES_DIR, f"X_{name}.npy"))
    y = np.load(os.path.join(FEATURES_DIR, f"y_{name}.npy"))
    return X, y


def load_classes():
    with open(os.path.join(FEATURES_DIR, "classes.txt")) as f:
        return [line.strip() for line in f if line.strip()]


def normalize(X_train, X_val, X_test):
    """Standardize using train-set stats only, to avoid leaking val/test info."""
    mean = X_train.mean()
    std = X_train.std() + 1e-8
    return (X_train - mean) / std, (X_val - mean) / std, (X_test - mean) / std, mean, std


def build_model(input_shape, n_classes):
    model = models.Sequential([
        layers.Input(shape=input_shape),

        layers.Conv2D(16, (3, 3), padding="same", activation="relu"),
        layers.BatchNormalization(),
        layers.MaxPooling2D((2, 2)),
        layers.Dropout(0.2),

        layers.Conv2D(32, (3, 3), padding="same", activation="relu"),
        layers.BatchNormalization(),
        layers.MaxPooling2D((2, 2)),
        layers.Dropout(0.2),

        layers.Conv2D(64, (3, 3), padding="same", activation="relu"),
        layers.BatchNormalization(),
        layers.MaxPooling2D((2, 2)),
        layers.Dropout(0.3),

        layers.GlobalAveragePooling2D(),
        layers.Dense(64, activation="relu"),
        layers.Dropout(0.3),
        layers.Dense(n_classes, activation="softmax"),
    ])
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=LEARNING_RATE),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


def plot_history(history):
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    axes[0].plot(history.history["loss"], label="train")
    axes[0].plot(history.history["val_loss"], label="val")
    axes[0].set_title("Loss")
    axes[0].legend()
    axes[1].plot(history.history["accuracy"], label="train")
    axes[1].plot(history.history["val_accuracy"], label="val")
    axes[1].set_title("Accuracy")
    axes[1].legend()
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "training_curves.png"), dpi=120)
    print(f"Saved training_curves.png to {OUT_DIR}/")
    plt.close(fig)


def plot_confusion_matrix(y_true, y_pred, class_names):
    cm = confusion_matrix(y_true, y_pred)
    fig, ax = plt.subplots(figsize=(7, 6))
    im = ax.imshow(cm, cmap="Greens")
    ax.set_xticks(range(len(class_names)))
    ax.set_yticks(range(len(class_names)))
    ax.set_xticklabels(class_names, rotation=45, ha="right")
    ax.set_yticklabels(class_names)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("True")
    ax.set_title("Confusion Matrix — Test Set")
    for i in range(len(class_names)):
        for j in range(len(class_names)):
            ax.text(j, i, cm[i, j], ha="center", va="center",
                     color="white" if cm[i, j] > cm.max() / 2 else "black")
    fig.colorbar(im, ax=ax)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "confusion_matrix.png"), dpi=120)
    print(f"Saved confusion_matrix.png to {OUT_DIR}/")
    plt.close(fig)


def main():
    print("Loading features...")
    X_train, y_train = load_split("train")
    X_val, y_val = load_split("val")
    X_test, y_test = load_split("test")
    class_names = load_classes()
    n_classes = len(class_names)

    print(f"Train: {X_train.shape}, Val: {X_val.shape}, Test: {X_test.shape}")
    print(f"Classes ({n_classes}): {class_names}")

    # Normalize using train stats
    X_train, X_val, X_test, mean, std = normalize(X_train, X_val, X_test)
    np.save(os.path.join(OUT_DIR, "norm_mean_std.npy"), np.array([mean, std]))

    # Add channel dimension for Conv2D: (N, n_mels, time_frames) -> (N, n_mels, time_frames, 1)
    X_train = X_train[..., np.newaxis]
    X_val = X_val[..., np.newaxis]
    X_test = X_test[..., np.newaxis]

    # --- Class weights: this is the part that matters given your 7:1 imbalance ---
    class_weight_values = compute_class_weight(
        class_weight="balanced", classes=np.unique(y_train), y=y_train
    )
    class_weight_dict = {i: w for i, w in enumerate(class_weight_values)}
    print("\nClass weights (higher = rarer class, penalized more if misclassified):")
    for i, name in enumerate(class_names):
        print(f"  {name}: {class_weight_dict.get(i, 1.0):.2f}")

    model = build_model(X_train.shape[1:], n_classes)
    model.summary()

    cb = [
        callbacks.EarlyStopping(monitor="val_loss", patience=8, restore_best_weights=True),
        callbacks.ModelCheckpoint(
            os.path.join(OUT_DIR, "best_model.keras"), monitor="val_accuracy", save_best_only=True
        ),
        callbacks.ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=4, min_lr=1e-6),
    ]

    print("\nTraining...")
    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        class_weight=class_weight_dict,
        callbacks=cb,
        verbose=2,
    )
    plot_history(history)

    print("\nEvaluating on test set...")
    test_loss, test_acc = model.evaluate(X_test, y_test, verbose=0)
    print(f"Test accuracy: {test_acc:.4f}  |  Test loss: {test_loss:.4f}")

    y_pred_probs = model.predict(X_test, verbose=0)
    y_pred = np.argmax(y_pred_probs, axis=1)

    print("\nClassification report:")
    print(classification_report(y_test, y_pred, target_names=class_names, digits=3))

    plot_confusion_matrix(y_test, y_pred, class_names)

    model.save(os.path.join(OUT_DIR, "final_model.keras"))
    print(f"\nSaved final model to {OUT_DIR}/final_model.keras")
    print(f"Saved best (early-stopped) model to {OUT_DIR}/best_model.keras")

    # Convert to TFLite for edge deployment (Raspberry Pi / gateway inference)
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    tflite_model = converter.convert()
    tflite_path = os.path.join(OUT_DIR, "acoustic_model.tflite")
    with open(tflite_path, "wb") as f:
        f.write(tflite_model)
    print(f"Saved TFLite model to {tflite_path} — this is what runs on the gateway.")


if __name__ == "__main__":
    main()

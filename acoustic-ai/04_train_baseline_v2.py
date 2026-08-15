"""
04_train_baseline_v2.py

Improvements over the first version, based on what the first run revealed:
  - Trains on the GROUP-SAFE split from 03_extract_features_v2.py (no more
    source-recording leakage inflating or deflating val/test numbers)
  - Adds SpecAugment-style augmentation (random time + frequency masking) on
    TRAINING data only -- this manufactures more effective diversity from
    FSC22's genuinely small ~9-10-recordings-per-class reality
  - Smaller model + L2 weight decay + higher dropout -- less capacity to
    memorize a small dataset
  - Lower learning rate, longer patience -- last run's val_loss got worse
    every epoch from epoch 1, which pairs with LR being too high for this
    little data, not just "needs more epochs"

Run: python 04_train_baseline_v2.py
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from sklearn.utils.class_weight import compute_class_weight
from sklearn.metrics import classification_report, confusion_matrix
import tensorflow as tf
from tensorflow.keras import layers, models, callbacks, regularizers

FEATURES_DIR = "features"
OUT_DIR = "models"
os.makedirs(OUT_DIR, exist_ok=True)

BATCH_SIZE = 16          # smaller batches = more gradient noise = mild regularization on small data
EPOCHS = 80
LEARNING_RATE = 3e-4      # lower than before (was 1e-3)
L2 = 1e-3

AUG_TIME_MASKS = 2        # SpecAugment: how many time-masks per training sample
AUG_TIME_MASK_WIDTH = 20  # max width in time-frames
AUG_FREQ_MASKS = 2
AUG_FREQ_MASK_WIDTH = 6   # max width in mel-bins


def load_split(name):
    X = np.load(os.path.join(FEATURES_DIR, f"X_{name}.npy"))
    y = np.load(os.path.join(FEATURES_DIR, f"y_{name}.npy"))
    return X, y


def load_classes():
    with open(os.path.join(FEATURES_DIR, "classes.txt")) as f:
        return [line.strip() for line in f if line.strip()]


def normalize(X_train, X_val, X_test):
    mean = X_train.mean()
    std = X_train.std() + 1e-8
    return (X_train - mean) / std, (X_val - mean) / std, (X_test - mean) / std, mean, std


def spec_augment(spec):
    """Applies random time and frequency masking to a single (n_mels, time) spectrogram.
    Operates on a numpy array; called per-sample inside the tf.data pipeline."""
    spec = spec.copy()
    n_mels, n_time = spec.shape
    fill_value = spec.min()  # mask with the quietest value in this clip, not zero

    for _ in range(AUG_FREQ_MASKS):
        f = np.random.randint(0, AUG_FREQ_MASK_WIDTH + 1)
        if f == 0 or f >= n_mels:
            continue
        f0 = np.random.randint(0, n_mels - f)
        spec[f0:f0 + f, :] = fill_value

    for _ in range(AUG_TIME_MASKS):
        t = np.random.randint(0, AUG_TIME_MASK_WIDTH + 1)
        if t == 0 or t >= n_time:
            continue
        t0 = np.random.randint(0, n_time - t)
        spec[:, t0:t0 + t] = fill_value

    return spec


def make_train_dataset(X, y, batch_size):
    def gen():
        idxs = np.arange(len(X))
        np.random.shuffle(idxs)
        for i in idxs:
            aug = spec_augment(X[i])
            yield aug[..., np.newaxis], y[i]

    ds = tf.data.Dataset.from_generator(
        gen,
        output_signature=(
            tf.TensorSpec(shape=(X.shape[1], X.shape[2], 1), dtype=tf.float32),
            tf.TensorSpec(shape=(), dtype=tf.int64),
        ),
    )
    return ds.batch(batch_size).prefetch(tf.data.AUTOTUNE)


def build_model(input_shape, n_classes):
    reg = regularizers.l2(L2)
    model = models.Sequential([
        layers.Input(shape=input_shape),

        layers.Conv2D(12, (3, 3), padding="same", activation="relu", kernel_regularizer=reg),
        layers.BatchNormalization(),
        layers.MaxPooling2D((2, 2)),
        layers.Dropout(0.3),

        layers.Conv2D(24, (3, 3), padding="same", activation="relu", kernel_regularizer=reg),
        layers.BatchNormalization(),
        layers.MaxPooling2D((2, 2)),
        layers.Dropout(0.3),

        layers.Conv2D(32, (3, 3), padding="same", activation="relu", kernel_regularizer=reg),
        layers.BatchNormalization(),
        layers.MaxPooling2D((2, 2)),
        layers.Dropout(0.4),

        layers.GlobalAveragePooling2D(),
        layers.Dense(32, activation="relu", kernel_regularizer=reg),
        layers.Dropout(0.4),
        layers.Dense(n_classes, activation="softmax"),
    ])
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=LEARNING_RATE),
        loss=tf.keras.losses.SparseCategoricalCrossentropy(),
        metrics=["accuracy"],
    )
    return model


def plot_history(history):
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    axes[0].plot(history.history["loss"], label="train")
    axes[0].plot(history.history["val_loss"], label="val")
    axes[0].set_title("Loss"); axes[0].legend()
    axes[1].plot(history.history["accuracy"], label="train")
    axes[1].plot(history.history["val_accuracy"], label="val")
    axes[1].set_title("Accuracy"); axes[1].legend()
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "training_curves_v2.png"), dpi=120)
    print(f"Saved training_curves_v2.png to {OUT_DIR}/")
    plt.close(fig)


def plot_confusion_matrix(y_true, y_pred, class_names):
    cm = confusion_matrix(y_true, y_pred)
    fig, ax = plt.subplots(figsize=(7, 6))
    im = ax.imshow(cm, cmap="Greens")
    ax.set_xticks(range(len(class_names))); ax.set_yticks(range(len(class_names)))
    ax.set_xticklabels(class_names, rotation=45, ha="right")
    ax.set_yticklabels(class_names)
    ax.set_xlabel("Predicted"); ax.set_ylabel("True")
    ax.set_title("Confusion Matrix — Test Set (v2)")
    for i in range(len(class_names)):
        for j in range(len(class_names)):
            ax.text(j, i, cm[i, j], ha="center", va="center",
                     color="white" if cm[i, j] > cm.max() / 2 else "black")
    fig.colorbar(im, ax=ax)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "confusion_matrix_v2.png"), dpi=120)
    print(f"Saved confusion_matrix_v2.png to {OUT_DIR}/")
    plt.close(fig)


def main():
    print("Loading GROUP-SAFE features (run 03_extract_features_v2.py first)...")
    X_train, y_train = load_split("train")
    X_val, y_val = load_split("val")
    X_test, y_test = load_split("test")
    class_names = load_classes()
    n_classes = len(class_names)

    print(f"Train: {X_train.shape}, Val: {X_val.shape}, Test: {X_test.shape}")

    X_train, X_val, X_test, mean, std = normalize(X_train, X_val, X_test)
    np.save(os.path.join(OUT_DIR, "norm_mean_std.npy"), np.array([mean, std]))

    X_val_ch = X_val[..., np.newaxis]
    X_test_ch = X_test[..., np.newaxis]

    class_weight_values = compute_class_weight(
        class_weight="balanced", classes=np.unique(y_train), y=y_train
    )
    class_weight_dict = {i: w for i, w in enumerate(class_weight_values)}
    print("\nClass weights:")
    for i, name in enumerate(class_names):
        print(f"  {name}: {class_weight_dict.get(i, 1.0):.2f}")

    train_ds = make_train_dataset(X_train, y_train, BATCH_SIZE)
    val_ds = tf.data.Dataset.from_tensor_slices((X_val_ch, y_val)).batch(BATCH_SIZE)

    model = build_model((X_train.shape[1], X_train.shape[2], 1), n_classes)
    model.summary()

    cb = [
        callbacks.EarlyStopping(monitor="val_loss", patience=15, restore_best_weights=True),
        callbacks.ModelCheckpoint(
            os.path.join(OUT_DIR, "best_model_v2.keras"), monitor="val_accuracy", save_best_only=True
        ),
        callbacks.ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=6, min_lr=1e-6),
    ]

    # class_weight isn't directly supported with tf.data + from_generator in all TF
    # versions the same way as with arrays, so we apply it via sample_weight instead.
    def add_sample_weight(x, y):
        sw = tf.gather(tf.constant([class_weight_dict[i] for i in range(n_classes)], dtype=tf.float32), y)
        return x, y, sw

    train_ds_weighted = train_ds.map(add_sample_weight)

    print("\nTraining (with SpecAugment on training data only)...")
    history = model.fit(
        train_ds_weighted,
        validation_data=val_ds,
        epochs=EPOCHS,
        callbacks=cb,
        verbose=2,
    )
    plot_history(history)

    print("\nEvaluating on test set...")
    test_loss, test_acc = model.evaluate(X_test_ch, y_test, verbose=0)
    print(f"Test accuracy: {test_acc:.4f}  |  Test loss: {test_loss:.4f}")

    y_pred_probs = model.predict(X_test_ch, verbose=0)
    y_pred = np.argmax(y_pred_probs, axis=1)

    print("\nClassification report:")
    print(classification_report(y_test, y_pred, target_names=class_names, digits=3, zero_division=0))

    plot_confusion_matrix(y_test, y_pred, class_names)

    model.save(os.path.join(OUT_DIR, "final_model_v2.keras"))
    print(f"\nSaved models to {OUT_DIR}/ (v2 suffix)")

    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    tflite_model = converter.convert()
    tflite_path = os.path.join(OUT_DIR, "acoustic_model_v2.tflite")
    with open(tflite_path, "wb") as f:
        f.write(tflite_model)
    print(f"Saved TFLite model to {tflite_path}")


if __name__ == "__main__":
    main()

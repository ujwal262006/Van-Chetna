"""
06_train_yamnet_classifier.py

Trains a small dense classifier on top of the YAMNet embeddings from
05_extract_yamnet_embeddings.py. This is the "baseline transfer learning"
approach -- much more sample-efficient than training a CNN from raw
spectrograms, and matches what published FSC22 research actually validates
(pretrained feature extractor + lightweight classifier head beats
training a CNN from scratch on this dataset size).

The classifier itself is intentionally simple (embeddings are already
information-rich): Dense -> Dropout -> Dense -> softmax. If this
significantly outperforms your from-scratch CNN runs (it should), that
confirms the pretrained-embedding approach is the right direction for the
rest of your 10 days -- don't go back to tuning the from-scratch CNN.

Run: python 06_train_yamnet_classifier.py
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from sklearn.utils.class_weight import compute_class_weight
from sklearn.metrics import classification_report, confusion_matrix
import tensorflow as tf
from tensorflow.keras import layers, models, callbacks, regularizers

FEATURES_DIR = "features_yamnet"
OUT_DIR = "models"
os.makedirs(OUT_DIR, exist_ok=True)

BATCH_SIZE = 32
EPOCHS = 100
LEARNING_RATE = 5e-4
L2 = 5e-4


def load_split(name):
    X = np.load(os.path.join(FEATURES_DIR, f"X_{name}.npy"))
    y = np.load(os.path.join(FEATURES_DIR, f"y_{name}.npy"))
    return X, y


def load_classes():
    with open(os.path.join(FEATURES_DIR, "classes.txt")) as f:
        return [line.strip() for line in f if line.strip()]


def build_model(input_dim, n_classes):
    reg = regularizers.l2(L2)
    model = models.Sequential([
        layers.Input(shape=(input_dim,)),
        layers.Dense(128, activation="relu", kernel_regularizer=reg),
        layers.BatchNormalization(),
        layers.Dropout(0.4),
        layers.Dense(64, activation="relu", kernel_regularizer=reg),
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
    axes[0].set_title("Loss"); axes[0].legend()
    axes[1].plot(history.history["accuracy"], label="train")
    axes[1].plot(history.history["val_accuracy"], label="val")
    axes[1].set_title("Accuracy"); axes[1].legend()
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "training_curves_yamnet.png"), dpi=120)
    print(f"Saved training_curves_yamnet.png to {OUT_DIR}/")
    plt.close(fig)


def plot_confusion_matrix(y_true, y_pred, class_names):
    cm = confusion_matrix(y_true, y_pred)
    fig, ax = plt.subplots(figsize=(7, 6))
    im = ax.imshow(cm, cmap="Greens")
    ax.set_xticks(range(len(class_names))); ax.set_yticks(range(len(class_names)))
    ax.set_xticklabels(class_names, rotation=45, ha="right")
    ax.set_yticklabels(class_names)
    ax.set_xlabel("Predicted"); ax.set_ylabel("True")
    ax.set_title("Confusion Matrix — YAMNet + Dense classifier")
    for i in range(len(class_names)):
        for j in range(len(class_names)):
            ax.text(j, i, cm[i, j], ha="center", va="center",
                     color="white" if cm[i, j] > cm.max() / 2 else "black")
    fig.colorbar(im, ax=ax)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, "confusion_matrix_yamnet.png"), dpi=120)
    print(f"Saved confusion_matrix_yamnet.png to {OUT_DIR}/")
    plt.close(fig)


def main():
    print("Loading YAMNet embeddings...")
    X_train, y_train = load_split("train")
    X_val, y_val = load_split("val")
    X_test, y_test = load_split("test")
    class_names = load_classes()
    n_classes = len(class_names)

    print(f"Train: {X_train.shape}, Val: {X_val.shape}, Test: {X_test.shape}")

    class_weight_values = compute_class_weight(
        class_weight="balanced", classes=np.unique(y_train), y=y_train
    )
    class_weight_dict = {i: w for i, w in enumerate(class_weight_values)}
    print("\nClass weights:")
    for i, name in enumerate(class_names):
        print(f"  {name}: {class_weight_dict.get(i, 1.0):.2f}")

    model = build_model(X_train.shape[1], n_classes)
    model.summary()

    cb = [
        callbacks.EarlyStopping(monitor="val_loss", patience=15, restore_best_weights=True),
        callbacks.ModelCheckpoint(
            os.path.join(OUT_DIR, "best_model_yamnet.keras"), monitor="val_accuracy", save_best_only=True
        ),
        callbacks.ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=6, min_lr=1e-6),
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
    print(classification_report(y_test, y_pred, target_names=class_names, digits=3, zero_division=0))

    plot_confusion_matrix(y_test, y_pred, class_names)

    model.save(os.path.join(OUT_DIR, "final_model_yamnet.keras"))
    print(f"\nSaved models to {OUT_DIR}/ (yamnet suffix)")
    print("\nNOTE: for deployment, the gateway needs to run BOTH YAMNet (feature")
    print("extractor) and this small classifier -- YAMNet itself is NOT converted")
    print("to TFLite here since it's a general-purpose model; we'll handle the")
    print("deployment pipeline once this classifier's accuracy is confirmed good.")


if __name__ == "__main__":
    main()

# ml_model.py
import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.utils import class_weight
from sklearn.cluster import KMeans
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Input

DATA_CSV = "customer_info.csv"
ACCURACY_PNG = "accuracy_plot.png"

class ProgressCallback(tf.keras.callbacks.Callback):
    def __init__(self, progress_dict, total_epochs):
        self.progress_dict = progress_dict
        self.total_epochs = total_epochs

    def on_epoch_end(self, epoch, logs=None):
        if self.progress_dict is not None:
            self.progress_dict['epoch'] = epoch + 1
            self.progress_dict['percent'] = int(((epoch + 1) / self.total_epochs) * 100)

def load_and_train(epochs=15, progress_callback_dict=None):
    df = pd.read_csv(DATA_CSV)
    df = df.dropna(subset=["gender", "region", "loyalty_tier"])
    # normalize text
    df["gender"] = df["gender"].astype(str).str.strip().str.title()
    df["loyalty_tier"] = df["loyalty_tier"].astype(str).str.strip().str.title()
    df["region"] = df["region"].astype(str).str.strip().str.title()

    # Convert signup_date to datetime
    df['signup_date'] = pd.to_datetime(df['signup_date'], errors='coerce', dayfirst=True, format='mixed')

    # Remove rows with empty loyalty_tier
    df = df[df["loyalty_tier"] != ""]

    # encoders per column
    encoders = {}
    for col in ["gender", "region", "loyalty_tier"]:
        le = LabelEncoder()
        df[col] = le.fit_transform(df[col].astype(str))
        encoders[col] = le

    # KMeans segments
    scaled_features = df[["gender", "region", "loyalty_tier"]].copy()
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(scaled_features)

    # Increase weight of loyalty_tier (index 2) to ensure distinct segments for Iron/Steel
    X_scaled[:, 2] *= 10.0

    kmeans = KMeans(n_clusters=5, random_state=42)
    df["customer_segment"] = kmeans.fit_predict(X_scaled)

    # Generate dynamic segment mapping based on majority loyalty tier in cluster
    segment_mapping = {}
    loyalty_le = encoders["loyalty_tier"]
    for i in range(5):
        cluster_rows = df[df["customer_segment"] == i]
        if not cluster_rows.empty:
            # Find most frequent loyalty tier in this cluster to name it
            mode_val = cluster_rows["loyalty_tier"].mode()[0]
            tier_name = loyalty_le.inverse_transform([mode_val])[0]
            segment_mapping[i] = f"{tier_name} Segment"
        else:
            segment_mapping[i] = f"Segment {i}"

    # NN training
    X = df[["gender", "region", "loyalty_tier"]].values
    y = tf.keras.utils.to_categorical(df["customer_segment"].values, num_classes=5)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Calculate class weights to handle imbalance (e.g., few Iron/Steel customers)
    unique_classes = np.unique(df["customer_segment"])
    weights = class_weight.compute_class_weight(
        class_weight='balanced',
        classes=unique_classes,
        y=df["customer_segment"]
    )
    class_weights_dict = {cls: weight for cls, weight in zip(unique_classes, weights)}

    model = Sequential([
        Input(shape=(3,)),
        Dense(16, activation='relu'),
        Dense(16, activation='relu'),
        Dense(5, activation='softmax')
    ])
    model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])

    callbacks = []
    if progress_callback_dict is not None:
        callbacks.append(ProgressCallback(progress_callback_dict, epochs))

    history = model.fit(X_train, y_train, validation_data=(X_test, y_test), epochs=epochs, batch_size=16, verbose=1, callbacks=callbacks, class_weight=class_weights_dict)

    # save accuracy plot
    plt.figure()
    plt.plot(history.history['accuracy'], label='Train Accuracy')
    plt.plot(history.history['val_accuracy'], label='Validation Accuracy')
    plt.xlabel('Epoch')
    plt.ylabel('Accuracy')
    plt.title('Model Accuracy per Epoch')
    plt.legend()
    plt.savefig(ACCURACY_PNG)
    plt.close()

    return {
        "df": df,
        "encoders": encoders,
        "scaler": scaler,
        "kmeans": kmeans,
        "model": model,
        "history": history,
        "segment_mapping": segment_mapping
    }
import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.compose import ColumnTransformer
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from sklearn.preprocessing import StandardScaler
from sklearn.utils.class_weight import compute_class_weight
from tensorflow import keras
from tensorflow.keras import layers, models

load_model = True


def preprocessing(df):
    # FIFO encoding
    fifo_cols = [col for col in df.columns if str(col).startswith('FIFO')]
    fifo_arr = df[fifo_cols].values  # This is a 2D NumPy array
    min_indices = np.argmin(fifo_arr, axis=1)
    df = df.drop(columns=fifo_cols)
    df['FIFO'] = min_indices

    # LRU encoding
    lru_cols = [col for col in df.columns if str(col).startswith('LRU')]
    lru_arr = df[lru_cols].values
    min_indices = np.argmin(lru_arr, axis=1)
    df = df.drop(columns=lru_cols)
    df['LRU'] = min_indices

    return df


df = pd.read_csv('log.csv', header=0)

# Collapse LRU and FIFO columns and hot encode
df = preprocessing(df)

# Separate features and target
# First column is the target (result)
y = df.iloc[:, 0].values
# Remaining 68 columns are features
# remove first 3 columns by their names resolved from positions
X = df.drop(columns=df.columns[:3])

# Identify all categorical columns
cat_cols = ['Level', 'Evicted index', 'FIFO', 'LRU']
# Identify numerical columns
num_cols = [c for c in X.columns if c not in cat_cols]
preprocess = ColumnTransformer(
    transformers=[
        ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), cat_cols),
        ('num', StandardScaler(), num_cols),
    ],
    remainder='drop'  # all columns covered, so drop the rest
)

print(f"Dataset shape: {X.shape}")
print(f"Target distribution: {np.bincount(y.astype(int))}")

# Split the data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

X_train_proc = preprocess.fit_transform(X_train)
X_test_proc = preprocess.transform(X_test)

# Build neural network for binary classification
model = models.Sequential([
    layers.Dense(128, activation='leaky_relu', input_shape=(91,), kernel_regularizer=keras.regularizers.l2(0.001)),
    layers.BatchNormalization(),
    layers.Dropout(0.3),
    layers.Dense(64, activation='leaky_relu'),
    layers.BatchNormalization(),
    layers.Dropout(0.3),
    layers.Dense(32, activation='leaky_relu'),
    layers.Dense(1, activation='sigmoid')  # Sigmoid for binary classification
])
model.compile(
    optimizer='adam',
    loss='binary_crossentropy',  # Binary classification loss
    metrics=['accuracy', tf.keras.metrics.AUC(name='auc')]  # Track accuracy and AUC
)
if load_model:
    model = keras.models.load_model('cache_eviction_model.keras')
# Display model architecture
model.summary()
# Train with early stopping to prevent overfitting
early_stopping = keras.callbacks.EarlyStopping(
    monitor='val_loss',
    patience=15,
    restore_best_weights=True
)
class_weight = compute_class_weight(
    class_weight='balanced',
    classes=np.unique(y_train),
    y=y_train
)
class_weight_dict = dict(enumerate(class_weight))

history = model.fit(
    X_train_proc, y_train,
    epochs=150,
    batch_size=32,
    validation_split=0.2,
    verbose=1,
    class_weight=class_weight_dict
)

# Evaluate on test set
test_loss, test_accuracy, test_auc = model.evaluate(X_test_proc, y_test)
print(f"\nTest Accuracy: {test_accuracy:.4f}")
print(f"Test AUC-ROC: {test_auc:.4f}")

# Get predictions
y_pred_prob = model.predict(X_test_proc)
y_pred = (y_pred_prob > 0.8).astype(int)  # Convert probabilities to 0/1

# Detailed evaluation
print("\nClassification Report:")
print(classification_report(y_test, y_pred, target_names=['Bad Eviction', 'Good Eviction']))

print("\nConfusion Matrix:")
print(confusion_matrix(y_test, y_pred))

# Save model and scaler
model.save('cache_eviction_model.keras')
import joblib

# scaler is your trained StandardScaler (after fit)
joblib.dump(preprocess, 'scaler.pkl')

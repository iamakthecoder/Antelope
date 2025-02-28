import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
from xgboost import XGBClassifier, XGBRegressor
import joblib
import os
import pickle

# Constants
CC_NAME = "illinois"
DATA_PATH = f"traindata/{CC_NAME}_output.txt"
MODEL_PATH = f"models/{CC_NAME}.pickle"

def load_data(file_path):
    """Load data from a text file and split into features and target."""
    data = []
    with open(file_path, 'r') as file:
        for line in file:
            values = line.strip().split()
            features = list(map(float, values[:-1]))  # Features
            target = float(values[-1])  # Target
            data.append((features, target))
    X, y = zip(*data)
    
    traindata = np.array(X)
    target = np.array(y)
    print(f"traindata shape: {traindata.shape}")
    print(f"target shape: {target.shape}")
    return traindata, target

def train_model(X_train, y_train):
    """Train an XGBoost regressor model."""
    # Check if the model already exists
    if os.path.exists(MODEL_PATH):
        print(f"Loading existing model from {MODEL_PATH}...")
        with open(MODEL_PATH, "rb") as f:
            model = pickle.load(f)
        # Train further on new data
        print("Training the existing model with new data...")
        model.fit(X_train, y_train)
        return model
    else:
        # Train a new model
        print("No existing model found. Training a new model...")
        model = XGBRegressor(n_estimators=100, max_depth=3, learning_rate=0.1)
        model.fit(X_train, y_train)
        return model

def evaluate_model(model, X_test, y_test):
    """Evaluate the model using root mean squared error (RMSE)."""
    y_pred = model.predict(X_test)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    print(f"Root Mean Squared Error: {rmse:.4f}")

def save_model(model, file_path):
    """Save the trained model to a file."""
    with open(file_path, "wb") as file_path:
        pickle.dump(model, file_path)
    print(f"Model saved to {file_path}")

def main():
    # Load data
    X, y = load_data(DATA_PATH)

    # Split data into train and test sets
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

    # Train the model
    model = train_model(X_train, y_train)

    # Evaluate the model
    evaluate_model(model, X_test, y_test)

    # Save the model
    save_model(model, MODEL_PATH)

if __name__ == "__main__":
    main()

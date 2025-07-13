import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, Input
from tensorflow.keras.models import load_model as keras_load_model, save_model

class TradingAIModel:
    def __init__(self, sequence_length=60):
        self.sequence_length = sequence_length
        self.model = self._build_model()

    def _build_model(self):
        model = Sequential()
        model.add(Input(shape=(self.sequence_length, 1)))
        model.add(LSTM(units=50, return_sequences=True))
        model.add(Dropout(0.2))
        model.add(LSTM(units=50, return_sequences=False))
        model.add(Dropout(0.2))
        model.add(Dense(units=25))
        model.add(Dense(units=1))
        model.compile(optimizer='adam', loss='mean_squared_error')
        return model

    def prepare_data(self, kline_data):
        df = pd.DataFrame(kline_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['close'] = df['close'].astype(float)

        scaler = MinMaxScaler(feature_range=(0,1))
        scaled_data = scaler.fit_transform(df['close'].values.reshape(-1,1))

        X, y = [], []
        for i in range(self.sequence_length, len(scaled_data)):
            X.append(scaled_data[i-self.sequence_length:i, 0])
            y.append(scaled_data[i, 0])

        return np.array(X), np.array(y), scaler

    def train(self, X, y, epochs=1, batch_size=1):
        self.model.fit(X, y, epochs=epochs, batch_size=batch_size)

    def save_model(self, filepath='ai_model/ai_model.h5'):
        save_model(self.model, filepath)

    def load_model(self, filepath='ai_model/ai_model.h5'):
        self.model = keras_load_model(filepath)

    def predict(self, X):
        return self.model.predict(X)

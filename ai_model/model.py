import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import joblib

class TradingAIModel:
    def __init__(self, n_estimators=100, random_state=42):
        self.model = RandomForestClassifier(n_estimators=n_estimators, random_state=random_state)

    def prepare_data(self, kline_data):
        df = pd.DataFrame(kline_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['close'] = df['close'].astype(float)
        df['future_return'] = df['close'].pct_change().shift(-1)
        df['target'] = (df['future_return'] > 0).astype(int)
        df.dropna(inplace=True)

        features = ['open', 'high', 'low', 'close', 'volume']
        X = df[features]
        y = df['target']
        return X, y

    def train(self, X, y):
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        self.model.fit(X_train, y_train)
        predictions = self.model.predict(X_test)
        accuracy = accuracy_score(y_test, predictions)
        print(f"Model Accuracy: {accuracy}")
        return accuracy

    def save_model(self, filepath='ai_model/ai_model.pkl'):
        joblib.dump(self.model, filepath)

    def load_model(self, filepath='ai_model/ai_model.pkl'):
        self.model = joblib.load(filepath)

    def predict(self, X):
        return self.model.predict(X)

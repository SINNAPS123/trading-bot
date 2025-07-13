import unittest
import numpy as np
from ai_model.model import TradingAIModel

class TestAIModel(unittest.TestCase):
    def setUp(self):
        self.model = TradingAIModel()
        self.kline_data = [
            [1672531200000, 47000, 47100, 46900, 47050, 100],
            [1672531260000, 47050, 47150, 47000, 47100, 120],
            [1672531320000, 47100, 47200, 47050, 47150, 110],
            [1672531380000, 47150, 47250, 47100, 47200, 130],
            [1672531440000, 47200, 47300, 47150, 47250, 140],
        ] * 20  # Repeat data to have enough for sequence

    def test_prepare_data(self):
        X, y, scaler = self.model.prepare_data(self.kline_data)
        self.assertEqual(X.shape[1], self.model.sequence_length)
        self.assertEqual(X.shape[0], y.shape[0])

    def test_train_and_predict(self):
        X, y, scaler = self.model.prepare_data(self.kline_data)
        self.model.train(X, y)
        prediction = self.model.predict(X)
        self.assertEqual(prediction.shape[0], y.shape[0])

if __name__ == '__main__':
    unittest.main()

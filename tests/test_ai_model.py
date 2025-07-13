import unittest
import numpy as np
import pandas as pd
from ai_model.dqn_model import DQNModel

class TestAIModel(unittest.TestCase):
    def setUp(self):
        self.model = DQNModel(5, 3)
        self.kline_data = [
            [1672531200000, 47000, 47100, 46900, 47050, 100],
            [1672531260000, 47050, 47150, 47000, 47100, 120],
            [1672531320000, 47100, 47200, 47050, 47150, 110],
            [1672531380000, 47150, 47250, 47100, 47200, 130],
            [1672531440000, 47200, 47300, 47150, 47250, 140],
        ] * 20  # Repeat data to have enough for sequence

    def test_prepare_data(self):
        X, y = self.model.prepare_data(self.kline_data)
        self.assertEqual(X.shape[1], self.model.state_size)
        self.assertEqual(X.shape[0], y.shape[0])

    def test_act(self):
        state = np.reshape(self.kline_data[-1][1:], [1, self.model.state_size])
        action = self.model.act(state)
        self.assertIn(action, [0, 1, 2])

if __name__ == '__main__':
    unittest.main()

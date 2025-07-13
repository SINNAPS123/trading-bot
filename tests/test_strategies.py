import unittest
import pandas as pd
from strategies.scalping_strategy import ScalpingStrategy

class TestScalpingStrategy(unittest.TestCase):

    def setUp(self):
        self.strategy = ScalpingStrategy()
        self.kline_data = [
            [1672531200000, 40000, 40100, 39900, 40050, 100],
            [1672531260000, 40050, 40150, 40000, 40100, 120],
            [1672531320000, 40100, 40200, 40050, 40150, 110],
            [1672531380000, 40150, 40250, 40100, 40200, 130],
            [1672531440000, 40200, 40300, 40150, 40250, 140],
            [1672531500000, 40250, 40350, 40200, 40300, 150],
            [1672531560000, 40300, 40400, 40250, 40350, 160],
            [1672531620000, 40350, 40450, 40300, 40400, 170],
            [1672531680000, 40400, 40500, 40350, 40450, 180],
            [1672531740000, 40450, 40550, 40400, 40500, 190],
            [1672531800000, 40500, 40600, 40450, 40550, 200],
            [1672531860000, 40550, 40650, 40500, 40600, 210],
            [1672531920000, 40600, 40700, 40550, 40650, 220],
            [1672531980000, 40650, 40750, 40600, 40700, 230],
            [1672532040000, 40700, 40800, 40650, 40750, 240]
        ]

    def test_generate_signals(self):
        signals_df = self.strategy.generate_signals(self.kline_data)
        self.assertIsInstance(signals_df, pd.DataFrame)
        self.assertIn('buy_signal', signals_df.columns)
        self.assertIn('sell_signal', signals_df.columns)

if __name__ == '__main__':
    unittest.main()

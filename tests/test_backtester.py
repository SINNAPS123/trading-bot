import unittest
import pandas as pd
from backtesting.backtester import Backtester

class TestBacktester(unittest.TestCase):
    def test_run_backtest(self):
        data = {
            'open': [100, 102, 101, 103, 105],
            'high': [103, 104, 103, 105, 106],
            'low': [99, 101, 100, 102, 104],
            'close': [102, 101, 103, 105, 104],
            'volume': [1000, 1200, 1100, 1300, 1400]
        }
        df = pd.DataFrame(data)
        backtester = Backtester(df, 'XBTUSDTM')
        final_balance = backtester.run_backtest()
        self.assertGreater(final_balance, 0)

if __name__ == '__main__':
    unittest.main()

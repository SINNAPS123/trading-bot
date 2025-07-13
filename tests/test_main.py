import unittest
from unittest.mock import MagicMock
from main import TradingBot

class TestTradingBot(unittest.TestCase):

    def setUp(self):
        self.bot = TradingBot()
        self.bot.kucoin_client = MagicMock()

    def test_graceful_stop(self):
        print("Running test_graceful_stop...")
        # Simulate an open position
        self.bot.kucoin_client.get_open_positions.return_value = [
            {
                'symbol': 'XBTUSDTM',
                'side': 'long',
                'contracts': 1
            }
        ]
        print("Simulated open positions.")

        # Call the graceful_stop method
        self.bot.graceful_stop()
        print("Called graceful_stop.")

        # Verify that the close order was placed
        self.bot.kucoin_client.place_market_order.assert_called_once_with('XBTUSDTM', 'sell', 1)
        self.assertFalse(self.bot.running)
        print("Assertions passed.")

suite = unittest.TestSuite()
suite.addTest(unittest.makeSuite(TestTradingBot))
runner = unittest.TextTestRunner()
runner.run(suite)

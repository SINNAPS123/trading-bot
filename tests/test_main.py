import unittest
from unittest.mock import MagicMock
from main import TradingBot

class TestTradingBot(unittest.TestCase):

    def setUp(self):
        self.bot = TradingBot()
        self.bot.kucoin_client.exchange = MagicMock()

    def test_graceful_stop(self):
        # Simulate an open position
        self.bot.kucoin_client.exchange.fetch_positions.return_value = [
            {
                'info': {'symbol': 'XBTUSDTM'},
                'symbol': 'XBTUSDTM',
                'side': 'long',
                'contracts': 1
            }
        ]

        # Call the graceful_stop method
        self.bot.graceful_stop()

        # Verify that the close order was placed
        self.bot.kucoin_client.exchange.create_market_order.assert_called_once_with('XBTUSDTM', 'sell', 1)
        self.assertFalse(self.bot.running)

if __name__ == '__main__':
    unittest.main()

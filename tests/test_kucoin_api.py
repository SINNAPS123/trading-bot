import unittest
from kucoin_api.test_client import TestKuCoinFuturesClient

class TestKucoinApi(unittest.TestCase):
    def setUp(self):
        self.client = TestKuCoinFuturesClient()

    def test_get_kline_data(self):
        kline_data = self.client.get_kline_data('XBTUSDTM', '1m')
        self.assertIsInstance(kline_data, list)
        self.assertGreater(len(kline_data), 0)

    def test_place_market_order(self):
        order = self.client.place_market_order('XBTUSDTM', 'buy', 1)
        self.assertIn('id', order)
        self.assertEqual(order['symbol'], 'XBTUSDTM')
        self.assertEqual(order['side'], 'buy')
        self.assertEqual(order['type'], 'market')

if __name__ == '__main__':
    unittest.main()

import os
import ccxt
from dotenv import load_dotenv

load_dotenv()

class KuCoinFuturesClient:
    def __init__(self):
        self.api_key = os.getenv("KUCOIN_API_KEY")
        self.api_secret = os.getenv("KUCOIN_API_SECRET")
        self.api_passphrase = os.getenv("KUCOIN_API_PASSPHRASE")

        self.exchange = ccxt.kucoinfutures({
            'apiKey': self.api_key,
            'secret': self.api_secret,
            'password': self.api_passphrase,
            'options': {
                'defaultType': 'future',
            },
        })

    def get_server_time(self):
        return self.exchange.fetch_time()

    def get_account_overview(self):
        return self.exchange.fetch_balance()

    def place_market_order(self, symbol, side, amount, leverage=1):
        self.exchange.set_leverage(leverage, symbol)
        order = self.exchange.create_market_order(symbol, side, amount)
        with open('trades.log', 'a') as f:
            f.write(f"Timestamp: {order['timestamp']}, Symbol: {order['symbol']}, Side: {order['side']}, Amount: {order['amount']}, Price: {order['price']}\\n")
        return order

    def get_order_details(self, order_id):
        return self.exchange.fetch_order(order_id)

    def get_kline_data(self, symbol, timeframe='1m', since=None, limit=100):
        return self.exchange.fetch_ohlcv(symbol, timeframe, since, limit)

    def get_open_positions(self):
        return self.exchange.fetch_positions()

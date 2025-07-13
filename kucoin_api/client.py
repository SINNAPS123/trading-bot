import os
from kucoin_futures.client import Market, Trade, User
from dotenv import load_dotenv

load_dotenv()

class KuCoinFuturesClient:
    def __init__(self):
        self.api_key = os.getenv("KUCOIN_API_KEY")
        self.api_secret = os.getenv("KUCOIN_API_SECRET")
        self.api_passphrase = os.getenv("KUCOIN_API_PASSPHRASE")
        self.market = Market(key=self.api_key, secret=self.api_secret, passphrase=self.api_passphrase, is_sandbox=True)
        self.trade = Trade(key=self.api_key, secret=self.api_secret, passphrase=self.api_passphrase, is_sandbox=True)
        self.user = User(key=self.api_key, secret=self.api_secret, passphrase=self.api_passphrase, is_sandbox=True)

    def get_server_time(self):
        return self.market.get_server_timestamp()

    def get_account_overview(self):
        return self.user.get_account_overview()

    def place_market_order(self, symbol, side, leverage, size):
        return self.trade.create_market_order(symbol=symbol, side=side, lever=leverage, size=size)

    def get_order_details(self, order_id):
        return self.trade.get_order_details(orderId=order_id)

    def get_kline_data(self, symbol, granularity, start_at=None, end_at=None):
        return self.market.get_kline(symbol=symbol, granularity=granularity, startAt=start_at, endAt=end_at)

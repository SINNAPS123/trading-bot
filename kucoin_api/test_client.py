import time

class TestKuCoinFuturesClient:
    def __init__(self):
        self.balance = {'USDT': {'total': 10000, 'free': 10000}}
        self.positions = {}
        self.orders = {}
        self.kline_data = []

    def get_server_time(self):
        return int(time.time() * 1000)

    def get_account_overview(self):
        return self.balance

    def place_market_order(self, symbol, side, amount, leverage=1):
        # Simulate placing a market order
        print(f"Simulating place_market_order: {symbol}, {side}, {amount}")
        order_id = f"sim_{int(time.time() * 1000)}"
        self.orders[order_id] = {
            'id': order_id,
            'symbol': symbol,
            'side': side,
            'amount': amount,
            'status': 'closed',
            'timestamp': int(time.time() * 1000)
        }
        # Simulate position change
        if symbol not in self.positions:
            self.positions[symbol] = {'contracts': 0}
        if side == 'buy':
            self.positions[symbol]['contracts'] += amount
        else:
            self.positions[symbol]['contracts'] -= amount
        return self.orders[order_id]

    def get_order_details(self, order_id):
        return self.orders.get(order_id)

    def get_kline_data(self, symbol, timeframe='1m', since=None, limit=100):
        # Return some simulated k-line data
        if not self.kline_data:
            for i in range(limit):
                self.kline_data.append([
                    int(time.time() * 1000) - (limit - i) * 60000,
                    10000 + i, 10000 + i + 10, 10000 + i - 10, 10000 + i, 100
                ])
        return self.kline_data

    def get_open_positions(self):
        return [
            {'symbol': symbol, **pos}
            for symbol, pos in self.positions.items()
            if pos.get('contracts', 0) != 0
        ]

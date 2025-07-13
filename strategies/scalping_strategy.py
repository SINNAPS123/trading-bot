import pandas as pd
import numpy as np

class ScalpingStrategy:
    def __init__(self, short_ema_period=5, long_ema_period=20, rsi_period=14, macd_fast_period=12, macd_slow_period=26, macd_signal_period=9):
        self.short_ema_period = short_ema_period
        self.long_ema_period = long_ema_period
        self.rsi_period = rsi_period
        self.macd_fast_period = macd_fast_period
        self.macd_slow_period = macd_slow_period
        self.macd_signal_period = macd_signal_period

    def _calculate_ema(self, data, period):
        return data['close'].ewm(span=period, adjust=False).mean()

    def _calculate_rsi(self, data, period):
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def _calculate_macd(self, data, fast_period, slow_period, signal_period):
        ema_fast = self._calculate_ema(data, fast_period)
        ema_slow = self._calculate_ema(data, slow_period)
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
        return macd_line, signal_line

    def generate_signals(self, kline_data):
        df = pd.DataFrame(kline_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['close'] = df['close'].astype(float)

        df['short_ema'] = self._calculate_ema(df, self.short_ema_period)
        df['long_ema'] = self._calculate_ema(df, self.long_ema_period)
        df['rsi'] = self._calculate_rsi(df, self.rsi_period)
        df['macd_line'], df['signal_line'] = self._calculate_macd(df, self.macd_fast_period, self.macd_slow_period, self.macd_signal_period)

        # Entry signal: short EMA crosses above long EMA, RSI is not overbought, and MACD line is above signal line
        df['buy_signal'] = np.where(
            (df['short_ema'] > df['long_ema']) &
            (df['rsi'] < 70) &
            (df['macd_line'] > df['signal_line']),
            1, 0
        )

        # Exit signal: short EMA crosses below long EMA or RSI is overbought
        df['sell_signal'] = np.where(
            (df['short_ema'] < df['long_ema']) |
            (df['rsi'] > 70),
            1, 0
        )

        return df

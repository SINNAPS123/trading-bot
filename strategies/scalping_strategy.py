import pandas as pd
import numpy as np
import ta

class ScalpingStrategy:
    def __init__(self, short_ema_period=5, long_ema_period=20, rsi_period=14, macd_fast_period=12, macd_slow_period=26, macd_signal_period=9, atr_period=14):
        self.short_ema_period = short_ema_period
        self.long_ema_period = long_ema_period
        self.rsi_period = rsi_period
        self.macd_fast_period = macd_fast_period
        self.macd_slow_period = macd_slow_period
        self.macd_signal_period = macd_signal_period
        self.atr_period = atr_period

    def _calculate_ema(self, data, period):
        return ta.trend.ema_indicator(data['close'], window=period)

    def _calculate_rsi(self, data, period):
        return ta.momentum.rsi(data['close'], window=period)

    def _calculate_macd(self, data, fast_period, slow_period, signal_period):
        macd = ta.trend.MACD(data['close'], window_fast=fast_period, window_slow=slow_period, window_sign=signal_period)
        return macd.macd(), macd.macd_signal()

    def _calculate_atr(self, high, low, close, period):
        return ta.volatility.average_true_range(high, low, close, window=period)

    def generate_signals(self, kline_data):
        df = pd.DataFrame(kline_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['close'] = df['close'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)

        df['short_ema'] = self._calculate_ema(df, self.short_ema_period)
        df['long_ema'] = self._calculate_ema(df, self.long_ema_period)
        df['rsi'] = self._calculate_rsi(df, self.rsi_period)
        df['macd_line'], df['signal_line'] = self._calculate_macd(df, self.macd_fast_period, self.macd_slow_period, self.macd_signal_period)
        df['macd_histogram'] = df['macd_line'] - df['signal_line']
        df['atr'] = self._calculate_atr(df['high'], df['low'], df['close'], self.atr_period)

        # Entry signal: short EMA crosses above long EMA, RSI is not overbought, and MACD histogram is positive
        df['buy_signal'] = np.where(
            (df['short_ema'] > df['long_ema']) &
            (df['rsi'] < 70) &
            (df['macd_histogram'] > 0) &
            (df['short_ema'].shift(1) < df['long_ema'].shift(1)),  # EMA crossover
            1, 0
        )

        # Exit signal: short EMA crosses below long EMA or RSI is overbought, and MACD histogram is negative
        df['sell_signal'] = np.where(
            ((df['short_ema'] < df['long_ema']) |
            (df['rsi'] > 70)) &
            (df['macd_histogram'] < 0) &
            (df['short_ema'].shift(1) > df['long_ema'].shift(1)),  # EMA crossover
            1, 0
        )

        # Stop-loss for buy positions
        df['stop_loss_buy'] = df['low'] - df['atr'] * 1.5

        # Stop-loss for sell positions
        df['stop_loss_sell'] = df['high'] + df['atr'] * 1.5

        return df

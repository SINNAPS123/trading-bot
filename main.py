import time
import logging
from threading import Thread
from kucoin_api.client import KuCoinFuturesClient
from strategies.scalping_strategy import ScalpingStrategy
from ai_model.model import TradingAIModel
from telegram_bot.bot import main as run_telegram_bot

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', filename='trades.log')

class TradingBot:
    def __init__(self):
        self.kucoin_client = KuCoinFuturesClient()
        self.strategy = ScalpingStrategy()
        self.ai_model = TradingAIModel()
        self.mode = 'test'  # 'test' or 'live'
        self.running = False
        self.symbol = 'XBTUSDTM'  # Example symbol

    def set_mode(self, mode):
        self.mode = mode

    def start(self):
        self.running = True
        logging.info("Trading bot started.")
        self.run()

    def stop(self):
        self.running = False
        logging.info("Trading bot stopped.")

    def graceful_stop(self):
        logging.info("Initiating graceful stop...")
        self.running = False
        open_positions = self.kucoin_client.get_open_positions()
        for position in open_positions:
            if float(position.get('contracts', 0)) > 0:
                symbol = position['symbol']
                side = 'sell' if position['side'] == 'long' else 'buy'
                amount = position['contracts']
                logging.info(f"Closing position for {symbol}...")
                self.kucoin_client.place_market_order(symbol, side, amount)
        logging.info("All positions closed. Bot stopped.")

    def run(self):
        while self.running:
            try:
                # 1. Fetch data
                kline_data = self.kucoin_client.get_kline_data(self.symbol, '1m')
                if not kline_data:
                    logging.warning("No kline data received.")
                    time.sleep(60)
                    continue

                # 2. Generate signals
                signals_df = self.strategy.generate_signals(kline_data)

                # 3. Get latest signal
                latest_signal = signals_df.iloc[-1]

                # 4. (Optional) AI-enhanced decision
                # X_latest = latest_signal[['open', 'high', 'low', 'close', 'volume']]
                # ai_prediction = self.ai_model.predict(X_latest)

                # 5. Execute trades
                if latest_signal['buy_signal'] and self.mode == 'live':
                    # Place buy order
                    logging.info(f"Placing buy order for {self.symbol}")
                    self.kucoin_client.place_market_order(self.symbol, 'buy', 1, leverage=3)
                elif latest_signal['sell_signal'] and self.mode == 'live':
                    # Place sell order
                    logging.info(f"Placing sell order for {self.symbol}")
                    self.kucoin_client.place_market_order(self.symbol, 'sell', 1, leverage=3)

                time.sleep(60)  # Wait for the next candle
            except Exception as e:
                logging.error(f"An error occurred: {e}")
                time.sleep(60)

if __name__ == '__main__':
    bot = TradingBot()

    # Start the Telegram bot in a separate thread
    telegram_thread = Thread(target=run_telegram_bot, args=(bot,))
    telegram_thread.daemon = True
    telegram_thread.start()

    # Keep the main thread alive to allow the Telegram bot to run
    while True:
        time.sleep(1)

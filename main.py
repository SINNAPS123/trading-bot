import asyncio
import logging
import signal
import os
import httpx
from dotenv import load_dotenv
from kucoin_api.client import KuCoinFuturesClient
from kucoin_api.test_client import TestKuCoinFuturesClient
from strategies.scalping_strategy import ScalpingStrategy
from ai_model.model import TradingAIModel
from telegram_bot.bot import run_telegram_bot
import ta

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', filename='trades.log')

class TradingBot:
    def __init__(self):
        self.mode = 'test'  # 'test' or 'live'
        self.kucoin_client = TestKuCoinFuturesClient() if self.mode == 'test' else KuCoinFuturesClient()
        self.strategy = ScalpingStrategy()
        self.ai_model = TradingAIModel()
        self.running = False
        self.symbol = 'XBTUSDTM'  # Example symbol
        self._stop_event = asyncio.Event()
        self.perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")

    def calculate_atr(self, df, period=14):
        return ta.volatility.AverageTrueRange(
            high=df['high'],
            low=df['low'],
            close=df['close'],
            window=period
        ).average_true_range().iloc[-1]

    async def get_market_analysis(self, symbol):
        if not self.perplexity_api_key:
            logging.warning("Perplexity API key not found.")
            return None

        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"Bearer {self.perplexity_api_key}",
                    "Content-Type": "application/json",
                }
                data = {
                    "model": "sonar-medium-online",
                    "messages": [
                        {"role": "system", "content": "You are an expert financial analyst. Provide a detailed market analysis and a prediction for the next hour."},
                        {"role": "user", "content": f"Provide a detailed market analysis for {symbol}, including key support and resistance levels, and a price prediction for the next hour."},
                    ],
                }
                response = await client.post("https://api.perplexity.ai/chat/completions", headers=headers, json=data)
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as e:
            logging.error(f"HTTP error occurred while fetching market analysis: {e}")
        except Exception as e:
            logging.error(f"An error occurred while fetching market analysis: {e}")
        return None

    def set_mode(self, mode):
        if self.mode != mode:
            self.mode = mode
            self.kucoin_client = TestKuCoinFuturesClient() if self.mode == 'test' else KuCoinFuturesClient()
            logging.info(f"Bot mode changed to {mode}.")

    def stop(self):
        self.running = False
        self._stop_event.set()
        logging.info("Trading bot stopped.")

    def graceful_stop(self):
        logging.info("Initiating graceful stop...")
        self.running = False
        open_positions = self.kucoin_client.get_open_positions()
        for position in open_positions:
            if float(position.get('contracts', 0)) != 0:
                symbol = position['symbol']
                side = 'sell' if position['side'] == 'long' else 'buy'
                amount = position['contracts']
                logging.info(f"Closing position for {symbol}...")
                self.kucoin_client.place_market_order(symbol, side, amount)
        logging.info("All positions closed. Bot stopped.")
        self._stop_event.set()

    async def retrain_model_periodically(self, interval=3600):
        while self.running:
            await asyncio.sleep(interval)
            logging.info("Starting periodic model retraining...")
            try:
                kline_data = self.kucoin_client.get_kline_data(self.symbol, '1m', limit=1000)
                X, y, _ = self.ai_model.prepare_data(kline_data)
                self.ai_model.train(X, y)
                self.ai_model.save_model()
                logging.info("Model retraining complete.")
            except Exception as e:
                logging.error(f"An error occurred during model retraining: {e}")

    async def run(self):
        self.running = True
        while self.running:
            try:
                # 1. Fetch data
                kline_data = self.kucoin_client.get_kline_data(self.symbol, '1m')
                if not kline_data:
                    logging.warning("No kline data received.")
                    await asyncio.sleep(60)
                    continue

                # 2. Generate signals
                signals_df = self.strategy.generate_signals(kline_data)

                # 3. Get latest signal
                latest_signal = signals_df.iloc[-1]

                # 4. (Optional) AI-enhanced decision
                # X_latest = latest_signal[['open', 'high', 'low', 'close', 'volume']]
                # ai_prediction = self.ai_model.predict(X_latest)

                # 5. Execute trades
                atr = self.calculate_atr(pd.DataFrame(kline_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']))
                stop_loss_price = latest_signal['close'] - atr * 1.5
                take_profit_price = latest_signal['close'] + atr * 3

                open_positions = self.kucoin_client.get_open_positions()

                if not open_positions:
                    if latest_signal['buy_signal'] and self.mode == 'live':
                        # Place buy order
                        logging.info(f"Placing buy order for {self.symbol} with SL: {stop_loss_price} and TP: {take_profit_price}")
                        self.kucoin_client.place_market_order(self.symbol, 'buy', 1, leverage=3, stop_loss_price=stop_loss_price, take_profit_price=take_profit_price)
                    elif latest_signal['sell_signal'] and self.mode == 'live':
                        # Place sell order
                        logging.info(f"Placing sell order for {self.symbol} with SL: {stop_loss_price} and TP: {take_profit_price}")
                        self.kucoin_client.place_market_order(self.symbol, 'sell', 1, leverage=3, stop_loss_price=stop_loss_price, take_profit_price=take_profit_price)
                else:
                    for position in open_positions:
                        if position['side'] == 'long' and (latest_signal['close'] <= stop_loss_price or latest_signal['close'] >= take_profit_price):
                            logging.info(f"Closing long position for {self.symbol} due to risk management.")
                            self.kucoin_client.place_market_order(self.symbol, 'sell', position['contracts'])
                        elif position['side'] == 'short' and (latest_signal['close'] >= stop_loss_price or latest_signal['close'] <= take_profit_price):
                            logging.info(f"Closing short position for {self.symbol} due to risk management.")
                            self.kucoin_client.place_market_order(self.symbol, 'buy', position['contracts'])

                await asyncio.sleep(60)  # Wait for the next candle
            except Exception as e:
                logging.error(f"An error occurred: {e}")
                await asyncio.sleep(60)

async def main():
    bot = TradingBot()

    loop = asyncio.get_running_loop()

    # Handle graceful shutdown
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown(bot)))

    telegram_task = loop.create_task(run_telegram_bot(bot))
    bot_task = loop.create_task(bot.run())
    retrain_task = loop.create_task(bot.retrain_model_periodically())

    # Keep the main function running
    await bot._stop_event.wait()

    # Wait for the Telegram bot and trading bot to finish
    await telegram_task
    await bot_task
    await retrain_task

async def shutdown(bot):
    print("Shutting down...")
    bot.graceful_stop()
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    asyncio.get_running_loop().stop()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot shutdown.")

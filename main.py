import asyncio
import logging
import signal
import os
import httpx
import pandas as pd
from dotenv import load_dotenv
from kucoin_api.client import KuCoinFuturesClient
from kucoin_api.test_client import TestKuCoinFuturesClient
from strategies.scalping_strategy import ScalpingStrategy
from ai_model.dqn_model import DQNModel
from telegram_bot.bot import run_telegram_bot
import ta

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', filename='trades.log', filemode='a')
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logging.getLogger().addHandler(console_handler)

class TradingBot:
    def __init__(self):
        self.mode = 'test'  # 'test' or 'live'
        self.kucoin_client = TestKuCoinFuturesClient() if self.mode == 'test' else KuCoinFuturesClient()
        self.strategy = ScalpingStrategy()
        self.state_size = 5  # open, high, low, close, volume
        self.action_size = 3  # hold, buy, sell
        self.ai_model = DQNModel(self.state_size, self.action_size)
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

    def calculate_trade_size(self, balance, risk_percentage):
        return (balance * risk_percentage) / 100

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
        self._stop_event.clear()
        self.running = True
        batch_size = 32
        logging.info("Trading bot started.")
        while self.running:
            try:
                # 1. Fetch data
                kline_data = self.kucoin_client.get_kline_data(self.symbol, '1m')
                if not kline_data:
                    logging.warning("No kline data received.")
                    await asyncio.sleep(60)
                    continue

                # 2. Prepare state
                latest_kline = kline_data[-1]
                state = np.reshape(latest_kline[1:], [1, self.state_size])

                # 3. Act
                action = self.ai_model.act(state)

                # 4. Execute trades
                reward = 0
                done = False
                if action == 1:  # Buy
                    # Place buy order
                    balance = self.kucoin_client.get_account_overview().get('USDT', {}).get('total', 0)
                    trade_size = self.calculate_trade_size(balance, 2)  # 2% risk
                    logging.info(f"Placing buy order for {self.symbol} with size {trade_size}")
                    self.kucoin_client.place_market_order(self.symbol, 'buy', trade_size, leverage=3)
                    reward = 1  # Example reward
                elif action == 2:  # Sell
                    # Place sell order
                    balance = self.kucoin_client.get_account_overview().get('USDT', {}).get('total', 0)
                    trade_size = self.calculate_trade_size(balance, 2)  # 2% risk
                    logging.info(f"Placing sell order for {self.symbol} with size {trade_size}")
                    self.kucoin_client.place_market_order(self.symbol, 'sell', trade_size, leverage=3)
                    reward = 1  # Example reward

                # 5. Get next state
                next_kline_data = self.kucoin_client.get_kline_data(self.symbol, '1m')
                next_latest_kline = next_kline_data[-1]
                next_state = np.reshape(next_latest_kline[1:], [1, self.state_size])

                # 6. Remember
                self.ai_model.remember(state, action, reward, next_state, done)

                # 7. Replay
                if len(self.ai_model.memory) > batch_size:
                    self.ai_model.replay(batch_size)

                await asyncio.sleep(60)  # Wait for the next candle
            except Exception as e:
                logging.error(f"An error occurred: {e}")
                await asyncio.sleep(60)
        logging.info("Trading bot stopped.")

async def main():
    bot = TradingBot()
    loop = asyncio.get_running_loop()

    # Handle graceful shutdown
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown(bot)))

    telegram_task = loop.create_task(run_telegram_bot(bot))
    # The bot will be started via Telegram command
    await bot._stop_event.wait()
    await telegram_task

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

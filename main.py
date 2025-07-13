import asyncio
import logging
import signal
import os
import httpx
import pandas as pd
import numpy as np
from dotenv import load_dotenv
from kucoin_api.client import KuCoinFuturesClient
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
        self.kucoin_client = KuCoinFuturesClient()
        self.strategy = ScalpingStrategy()
        self.state_size = 5  # open, high, low, close, volume
        self.action_size = 3  # hold, buy, sell
        self.ai_model = DQNModel(self.state_size, self.action_size)
        self.running = False
        self.symbol = 'XBTUSDTM'  # Example symbol
        self._stop_event = asyncio.Event()
        self.is_trading_active = False
        self.perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")
        self.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")

    async def send_telegram_message(self, message):
        if not self.telegram_bot_token or not self.telegram_chat_id:
            logging.warning("Telegram bot token or chat ID not set. Cannot send message.")
            return
        url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
        params = {
            'chat_id': self.telegram_chat_id,
            'text': message,
            'parse_mode': 'Markdown'
        }
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=params)
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                logging.error(f"HTTP error occurred while sending Telegram message: {e}")
            except Exception as e:
                logging.error(f"An error occurred while sending Telegram message: {e}")

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
            await self.send_telegram_message("🧠 Starting periodic model retraining...")
            try:
                kline_data = self.kucoin_client.get_kline_data(self.symbol, '1m', limit=1000)
                X, y = self.ai_model.prepare_data(kline_data)
                self.ai_model.replay(len(self.ai_model.memory) if len(self.ai_model.memory) < 32 else 32)
                self.ai_model.save("dqn_model.h5")
                logging.info("Model retraining complete.")
                await self.send_telegram_message("✅ Model retraining complete.")
            except Exception as e:
                logging.error(f"An error occurred during model retraining: {e}")
                await self.send_telegram_message(f"🚨 An error occurred during model retraining: {e}")

    async def run(self):
        self._stop_event.clear()
        self.running = True
        self.is_trading_active = True
        batch_size = 32
        logging.info("Trading bot started.")
        await self.send_telegram_message("🤖 **Trading Bot Started**\nInitializing...")

        # Dynamically select symbol
        try:
            await self.send_telegram_message("🔍 Selecting optimal trading pair...")
            account_balance = self.kucoin_client.get_account_overview()
            # Find the currency with the highest balance, excluding the base currency
            # In a real scenario, you might want to have a list of preferred currencies to trade
            quote_currency = max(
                (k for k, v in account_balance.items() if k != self.base_currency),
                key=lambda k: account_balance[k].get('total', 0)
            )
            self.symbol = f"{quote_currency}{self.base_currency}M"
            await self.send_telegram_message(f"📈 Selected trading pair: {self.symbol}")

            market_analysis = await self.get_market_analysis(self.symbol)
            if market_analysis:
                await self.send_telegram_message(f"📊 **Market Analysis for {self.symbol}**\n{market_analysis}")
            else:
                await self.send_telegram_message(f"⚠️ Could not retrieve market analysis for {self.symbol}.")

        except Exception as e:
            logging.error(f"Error selecting symbol: {e}")
            await self.send_telegram_message(f"🚨 Error selecting symbol: {e}\nBot will not start.")
            self.stop()
            return

        while self.running:
            if not self.is_trading_active:
                await asyncio.sleep(10)
                continue

            try:
                # 1. Fetch data
                logging.info("Fetching market data...")
                kline_data = self.kucoin_client.get_kline_data(self.symbol, '1m')
                if not kline_data:
                    logging.warning("No kline data received. Waiting...")
                    await self.send_telegram_message("⏳ No market data received. The bot will retry shortly.")
                    await asyncio.sleep(60)
                    continue
                logging.info(f"Successfully fetched {len(kline_data)} k-line data points.")

                # 2. Prepare state
                latest_kline = kline_data[-1]
                state = np.reshape(latest_kline[1:], [1, self.state_size])
                logging.info(f"Current market price for {self.symbol}: {latest_kline[4]}")
                await self.send_telegram_message(f"📊 **Market Update**\n**Symbol:** `{self.symbol}`\n**Price:** `{latest_kline[4]}`")

                # 3. Act
                logging.info("AI model is making a decision...")
                action = self.ai_model.act(state)
                action_map = {0: "Hold", 1: "Buy", 2: "Sell"}
                logging.info(f"AI model action: {action_map[action]}")
                await self.send_telegram_message(f"🧠 **AI Decision**\n**Action:** `{action_map[action]}`")

                # 4. Execute trades
                reward = 0
                done = False
                if action == 1:  # Buy
                    trade_size = self.calculate_trade_size(self.kucoin_client.get_account_overview().get('USDT', {}).get('total', 0), 2)
                    atr = self.calculate_atr(pd.DataFrame(kline_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']))
                    stop_loss = latest_kline[3] - atr * 1.5
                    take_profit = latest_kline[4] + atr * 2

                    logging.info(f"Placing buy order for {self.symbol} with size {trade_size}")
                    message = (f"📈 **Placing Buy Order**\n"
                                f"**Symbol:** `{self.symbol}`\n"
                                f"**Size:** `{trade_size}`\n"
                                f"**Stop-Loss:** `{stop_loss:.2f}`\n"
                                f"**Take-Profit:** `{take_profit:.2f}`")
                    await self.send_telegram_message(message)
                    self.kucoin_client.place_market_order(self.symbol, 'buy', trade_size, leverage=3, stop_loss=stop_loss, take_profit=take_profit)
                    reward = 1  # Example reward

                elif action == 2:  # Sell
                    trade_size = self.calculate_trade_size(self.kucoin_client.get_account_overview().get('USDT', {}).get('total', 0), 2)
                    atr = self.calculate_atr(pd.DataFrame(kline_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']))
                    stop_loss = latest_kline[2] + atr * 1.5
                    take_profit = latest_kline[4] - atr * 2

                    logging.info(f"Placing sell order for {self.symbol} with size {trade_size}")
                    message = (f"📉 **Placing Sell Order**\n"
                                f"**Symbol:** `{self.symbol}`\n"
                                f"**Size:** `{trade_size}`\n"
                                f"**Stop-Loss:** `{stop_loss:.2f}`\n"
                                f"**Take-Profit:** `{take_profit:.2f}`")
                    await self.send_telegram_message(message)
                    self.kucoin_client.place_market_order(self.symbol, 'sell', trade_size, leverage=3, stop_loss=stop_loss, take_profit=take_profit)
                    reward = 1  # Example reward

                # 5. Get next state
                next_kline_data = self.kucoin_client.get_kline_data(self.symbol, '1m')
                next_latest_kline = next_kline_data[-1]
                next_state = np.reshape(next_latest_kline[1:], [1, self.state_size])

                # 6. Remember
                self.ai_model.remember(state, action, reward, next_state, done)

                # 7. Replay
                if len(self.ai_model.memory) > batch_size:
                    logging.info("AI model is learning from recent trades...")
                    self.ai_model.replay(batch_size)
                    await self.send_telegram_message("🧠 The AI model is learning from recent trades.")

                logging.info("Waiting for the next market candle...")
                await asyncio.sleep(60)  # Wait for the next candle
            except Exception as e:
                logging.error(f"An error occurred: {e}")
                await self.send_telegram_message(f"🚨 **An Error Occurred**\n`{e}`\nThe bot will continue after a short delay.")
                await asyncio.sleep(60)
        logging.info("Trading bot stopped.")
        await self.send_telegram_message("🛑 **Trading Bot Stopped**")

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

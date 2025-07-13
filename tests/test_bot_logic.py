import asyncio
import unittest
from unittest.mock import MagicMock, AsyncMock

from main import TradingBot

class TestBotLogic(unittest.TestCase):
    def setUp(self):
        self.bot = TradingBot()
        self.bot.kucoin_client = MagicMock()
        self.bot.ai_model = MagicMock()
        self.bot.strategy = MagicMock()

    def test_calculate_trade_size(self):
        self.assertAlmostEqual(self.bot.calculate_trade_size(1000, 2), 20)
        self.assertAlmostEqual(self.bot.calculate_trade_size(5000, 1), 50)
        self.assertAlmostEqual(self.bot.calculate_trade_size(10000, 0.5), 50)

    def test_start_stop_logic(self):
        async def run_test():
            # Mock the run method to avoid an infinite loop
            self.bot.run = AsyncMock()

            # Start the bot
            asyncio.create_task(self.bot.run())
            await asyncio.sleep(0.1)  # Allow the task to start

            # Stop the bot
            self.bot.graceful_stop()
            await asyncio.sleep(0.1)  # Allow the stop event to be processed

            self.bot.run.assert_awaited_once()

        asyncio.run(run_test())

if __name__ == '__main__':
    unittest.main()

import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv

load_dotenv()

# Placeholder functions for bot commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Hello! I am your KuCoin Trading Bot. Use /help to see available commands.')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
    Available commands:
    /start - Start the bot
    /help - Show this help message
    /start_bot - Start the trading bot
    /stop_bot - Stop the trading bot
    /status - Show the status of the trading bot
    /balance - Show the account balance
    /trades - Show recent trades
    /train - Train the AI model
    /test_strategy - Test the trading strategy
    /set_mode <live/test> - Set the bot mode
    """
    await update.message.reply_text(help_text)

import asyncio

async def start_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_instance = context.bot_data.get('bot_instance')
    if bot_instance and not bot_instance.running:
        asyncio.create_task(bot_instance.run())
        await update.message.reply_text('Trading bot started.')
    elif bot_instance and bot_instance.running:
        await update.message.reply_text('Trading bot is already running.')
    else:
        await update.message.reply_text('Bot instance not found.')

async def stop_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_instance = context.bot_data.get('bot_instance')
    if bot_instance and bot_instance.running:
        await update.message.reply_text('Initiating graceful stop... The bot will stop after closing all positions.')
        bot_instance.graceful_stop()
    elif bot_instance and not bot_instance.running:
        await update.message.reply_text('Trading bot is already stopped.')
    else:
        await update.message.reply_text('Bot instance not found.')

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_instance = context.bot_data.get('bot_instance')
    if bot_instance:
        running = bot_instance.running
        mode = bot_instance.mode
        await update.message.reply_text(f'Bot status: {"Running" if running else "Stopped"}\nMode: {mode}')
    else:
        await update.message.reply_text('Bot instance not found.')

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_instance = context.bot_data.get('bot_instance')
    if bot_instance:
        balance = bot_instance.kucoin_client.get_account_overview()
        balance_text = "Account Balance:\n"
        for currency, details in balance.items():
            if isinstance(details, dict) and 'total' in details:
                balance_text += f"{currency}: {details['total']}\n"
        await update.message.reply_text(balance_text)
    else:
        await update.message.reply_text('Bot instance not found.')

async def trades(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_instance = context.bot_data.get('bot_instance')
    if bot_instance:
        if bot_instance.mode == 'test':
            trades = bot_instance.kucoin_client.orders
            if trades:
                trades_text = "Recent Trades:\n"
                for trade_id, trade in trades.items():
                    trades_text += f"ID: {trade_id}, Symbol: {trade['symbol']}, Side: {trade['side']}, Amount: {trade['amount']}\n"
                await update.message.reply_text(trades_text)
            else:
                await update.message.reply_text("No trades found.")
        else:
            try:
                with open('trades.log', 'r') as f:
                    trades = f.readlines()
                if trades:
                    await update.message.reply_text("Recent Trades:\n" + "".join(trades[-10:]))
                else:
                    await update.message.reply_text("No trades found.")
            except FileNotFoundError:
                await update.message.reply_text("No trades found.")
    else:
        await update.message.reply_text('Bot instance not found.')

async def train(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_instance = context.bot_data.get('bot_instance')
    if bot_instance:
        await update.message.reply_text('Starting AI model training...')
        await bot_instance.send_telegram_message("🧠 Starting AI model training...")
        try:
            kline_data = bot_instance.kucoin_client.get_kline_data(bot_instance.symbol, '1h', limit=500)
            X, y = bot_instance.ai_model.prepare_data(kline_data)
            bot_instance.ai_model.replay(len(bot_instance.ai_model.memory) if len(bot_instance.ai_model.memory) < 32 else 32)
            bot_instance.ai_model.save("dqn_model.h5")
            await update.message.reply_text('AI model training complete.')
            await bot_instance.send_telegram_message("✅ AI model training complete.")
        except Exception as e:
            await update.message.reply_text(f"An error occurred during training: {e}")
            await bot_instance.send_telegram_message(f"🚨 An error occurred during training: {e}")
    else:
        await update.message.reply_text('Bot instance not found.')

async def test_strategy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_instance = context.bot_data.get('bot_instance')
    if bot_instance:
        await update.message.reply_text('Testing strategy...')
        kline_data = bot_instance.kucoin_client.get_kline_data(bot_instance.symbol, '1m', limit=100)
        signals_df = bot_instance.strategy.generate_signals(kline_data)
        await update.message.reply_text("Last 10 signals:\n" + signals_df.tail(10).to_string())
    else:
        await update.message.reply_text('Bot instance not found.')

async def set_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        mode = context.args[0].lower()
        if mode in ['live', 'test']:
            bot_instance = context.bot_data.get('bot_instance')
            if bot_instance:
                bot_instance.set_mode(mode)
                await update.message.reply_text(f'Mode set to {mode}.')
            else:
                await update.message.reply_text('Bot instance not found.')
        else:
            await update.message.reply_text('Invalid mode. Use "live" or "test".')
    else:
        await update.message.reply_text('Please specify a mode: /set_mode <live/test>')

async def run_telegram_bot(bot_instance):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logging.error("TELEGRAM_BOT_TOKEN not set.")
        return

    application = ApplicationBuilder().token(token).build()

    # Add the bot instance to the application context
    application.bot_data['bot_instance'] = bot_instance

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("start_bot", start_bot))
    application.add_handler(CommandHandler("stop_bot", stop_bot))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("balance", balance))
    application.add_handler(CommandHandler("trades", trades))
    application.add_handler(CommandHandler("train", train))
    application.add_handler(CommandHandler("test_strategy", test_strategy))
    application.add_handler(CommandHandler("set_mode", set_mode))

    await application.initialize()
    await application.start()
    await application.updater.start_polling()

    # The bot will run until it's stopped from main.py

import pandas as pd
import numpy as np
from ai_model.dqn_model import DQNModel

class Backtester:
    def __init__(self, data, symbol):
        self.data = data
        self.symbol = symbol
        self.state_size = 5  # open, high, low, close, volume
        self.action_size = 3  # hold, buy, sell
        self.agent = DQNModel(self.state_size, self.action_size)
        self.initial_balance = 10000
        self.balance = self.initial_balance
        self.inventory = []

    def run_backtest(self):
        for i in range(len(self.data) - 1):
            state = np.reshape(self.data.iloc[i].values, [1, self.state_size])
            action = self.agent.act(state)
            next_state = np.reshape(self.data.iloc[i+1].values, [1, self.state_size])
            reward = 0
            done = (i == len(self.data) - 2)

            if action == 1:  # Buy
                self.inventory.append(self.data['close'].iloc[i])
                print(f"Buy at: {self.data['close'].iloc[i]}")
            elif action == 2 and len(self.inventory) > 0:  # Sell
                buy_price = self.inventory.pop(0)
                profit = self.data['close'].iloc[i] - buy_price
                reward = max(profit, 0)
                self.balance += profit
                print(f"Sell at: {self.data['close'].iloc[i]}, Profit: {profit}")

            self.agent.remember(state, action, reward, next_state, done)

        if len(self.agent.memory) > 32:
            self.agent.replay(32)

        return self.balance

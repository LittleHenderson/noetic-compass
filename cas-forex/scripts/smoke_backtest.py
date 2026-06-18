import sys; sys.path.insert(0, r'C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex'); sys.path.insert(0, r'C:\Users\wakil\OneDrive\Desktop\tksCAS\noetic-compass-scaffold\noetic-compass')
import numpy as np
from datetime import datetime, timedelta
np.random.seed(42)
base = 1.0800; bars = []; t = datetime(2026, 5, 1, 8, 0)
for i in range(200):
    change = np.random.normal(0.00002, 0.0003); base += change
    bars.append(dict(timestamp=(t+timedelta(minutes=i*5)).isoformat(), open=round(base-change,5),
        high=round(base+abs(change)*2,5), low=round(base-abs(change)*2,5), close=round(base,5), volume=100))

from cas_forex.backtest.engine import BacktestEngine
r = BacktestEngine().run(bars, 'EUR/USD').summary()
print('BACKTEST: %d trades | %d won | %d lost | PnL $%.2f | Sharpe %.2f' % (r['total_trades'], r['winning_trades'], r['losing_trades'], r['total_profit_account'], r['sharpe_ratio']))

from cas_forex.sweep.sweeper import ProfitSweeper
from cas_forex.schemas.sweep import ProfitSweepPolicy, SweepMode
tx = ProfitSweeper(ProfitSweepPolicy(mode=SweepMode.AUTO, min_profit_threshold=5)).execute_sweep(10000, 50, 0)
print('SWEEP: %s | savings $%.2f | reinvest $%.2f' % (tx.status.value, tx.savings_amount, tx.reinvest_amount))

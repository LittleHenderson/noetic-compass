import sys; sys.path.insert(0, r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas-forex")
import numpy as np; from datetime import datetime, timedelta
np.random.seed(42)
def make_bars(n, tf_min, start, trend=0.0):
    base = 1.08; bars = []; t = start
    for i in range(n):
        c = np.random.normal(trend, 0.0003); base += c
        bars.append(dict(timestamp=(t+timedelta(minutes=i*tf_min)).isoformat(), 
            open=round(base-c,5), high=round(base+abs(c)*2,5), low=round(base-abs(c)*2,5), close=round(base,5), volume=100))
    return bars
t0 = datetime(2026,5,1,8,0)
frames = {'M5': make_bars(200,5,t0,0.00002), 'H1': make_bars(100,60,t0,0.00003), 
          'H4': make_bars(50,240,t0,0.00005), 'D1': make_bars(30,1440,t0,0.00008)}
from cas_forex.mtfa import MultiTimeframeAnalyzer, TradingStyle
for style in [TradingStyle.SCALPING, TradingStyle.DAY, TradingStyle.SWING, TradingStyle.POSITION]:
    mtfa = MultiTimeframeAnalyzer(style)
    sig = mtfa.analyze('EUR/USD', frames)
    print('%10s: trend=%s signal=%s ready=%s conf=%.2f tfs=%s/%s/%s' % (style.value, sig.trend_direction, 
        sig.signal_direction, sig.entry_ready, sig.confidence, sig.trend_tf, sig.signal_tf, sig.entry_tf))
print('done')

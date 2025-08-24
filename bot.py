import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import requests
import time
import warnings
import os

# Suppress NumPy reload warning
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=UserWarning, message="The NumPy module was reloaded")
    import pandas as pd

# NTFY configuration (topic: LSBot)
NTFY_TOPIC = "LSBot"
NTFY_URL = f"https://ntfy.sh/{NTFY_TOPIC}"

def send_to_ntfy(message):
    try:
        requests.post(NTFY_URL, data=message.encode("utf-8"))
        print("Message sent to ntfy!")
    except Exception as e:
        print("Failed to send message:", e)

# Fetch historical data
def fetch_data(tickers, period='2y', retries=3, delay=2):
    data_dict = {}
    failed_tickers = []
    end_date = datetime.now()
    start_date = end_date - timedelta(days=int(period.replace('y',''))*365)
    for ticker in tickers:
        for attempt in range(retries):
            try:
                df = yf.download(ticker, start=start_date, end=end_date, progress=False, auto_adjust=True)
                if df.empty:
                    raise ValueError(f"No historical data for {ticker}")
                df = df[['Close']].rename(columns={'Close': ticker})
                df.index = pd.to_datetime(df.index)
                data_dict[ticker] = df[ticker].squeeze().copy()
                time.sleep(delay)
                break
            except Exception as e:
                if attempt == retries-1:
                    failed_tickers.append(ticker)
                time.sleep(delay)
    if data_dict:
        df = pd.DataFrame(data_dict)
        df.index = pd.to_datetime(df.index)
        df.index.name = "Date"
        return df, failed_tickers
    return None, failed_tickers

# Days to next quarter-end
def days_to_quarter_end(current_date):
    quarter_ends = [datetime(current_date.year, m, d) for m,d in [(3,31),(6,30),(9,30),(12,31)]]
    next_q = min([q for q in quarter_ends if q >= current_date], default=datetime(current_date.year+1,3,31))
    return (next_q - current_date).days

# Main
tickers = ['SPY','QQQ','IEF','VT']
data, failed_tickers = fetch_data(tickers)
if data is None:
    send_to_ntfy(f"Error: Could not fetch data for {', '.join(failed_tickers)}")
    exit()

# Moving averages
moving_averages = {
    'SPY_20w': data['SPY'].rolling(100).mean(),
    'QQQ_20w': data['QQQ'].rolling(100).mean(),
    'SPY_200d': data['SPY'].rolling(200).mean(),
    'QQQ_220d': data['QQQ'].rolling(220).mean(),
    'IEF_50d': data['IEF'].rolling(50).mean(),
    'VT_20d': data['VT'].rolling(20).mean() if 'VT' in data.columns else None
}

latest_prices = data.iloc[-1]
latest_ma = {key: ma.iloc[-1] if ma is not None else None for key, ma in moving_averages.items()}

signals = {key: latest_prices[key.split('_')[0]] > latest_ma[key] if latest_ma[key] is not None else False
           for key in moving_averages.keys() if latest_ma[key] is not None}

days_left = days_to_quarter_end(data.index[-1])

# LS3.0 Implementation Signals (correct logic)
spy_200 = latest_ma['SPY_200d']
spy_upper = spy_200 * 1.0175
spy_lower = spy_200 * 0.9825

ief_50 = latest_ma['IEF_50d']
ief_upper = ief_50 * 1.02
ief_lower = ief_50 * 0.98

signal_1 = "On" if latest_prices['SPY'] > spy_upper or latest_prices['SPY'] >= spy_lower else "Off"
signal_2 = "On" if latest_prices['IEF'] > ief_upper or latest_prices['IEF'] >= ief_lower else "Off"

# Implementable positioning (exact original logic)
ls3_impl = "3LUS" if signal_1 == "On" and signal_2 == "On" else "Cash"

# For pretty display, map signals to emojis
signal_1_pretty = "✅ On" if signal_1 == "On" else "❌ Off"
signal_2_pretty = "✅ On" if signal_2 == "On" else "❌ Off"

ls3_message = f"""
📊 LS3.0 Implementation
------------------------
Signal 1 (SPY 200d MA ±1.75%): {signal_1_pretty}
Signal 2 (IEF 50d MA ±2%): {signal_2_pretty}
Positioning: {ls3_impl}
"""

# LS3.0 Overview
ls3_overview = f"""
📊 LS3.0: The Last Dance
------------------------
SPX 200d MA: {'above' if signals['SPY_200d'] else 'below'}
IEF 50d MA: {'above' if signals['IEF_50d'] else 'below'}
Positioning: {'3LUS' if signals['SPY_200d'] and signals['IEF_50d'] else '3TYL' if signals['IEF_50d'] and not signals['SPY_200d'] else 'Cash'}
"""

# LS2.0 Overview
ls2_positions = []
if signals['SPY_200d']:
    ls2_positions.append("3LUS")
if signals['QQQ_220d']:
    ls2_positions.append("LQQ3")
if signals['IEF_50d']:
    ls2_positions.append("3TYL")
if not ls2_positions:
    ls2_positions.append("Cash")

ls2_message = f"""
📊 LS2.0: The Challenger
------------------------
SPX 200d MA: {'above' if signals['SPY_200d'] else 'below'}
NDX 220d MA: {'above' if signals['QQQ_220d'] else 'below'}
IEF 50d MA: {'above' if signals['IEF_50d'] else 'below'}
Positioning: {', '.join(ls2_positions)}
Days to quarter-end: {days_left}
"""

# LS1.0 Overview
ls1_positions = []
if signals['SPY_20w']:
    ls1_positions.append("3LUS")
if signals['QQQ_20w']:
    ls1_positions.append("LQQ3")
if not ls1_positions:
    ls1_positions.append("Cash")

ls1_message = f"""
📊 LS1.0: The OG
------------------------
SPX 20w MA: {'above' if signals['SPY_20w'] else 'below'}
NDX 20w MA: {'above' if signals['QQQ_20w'] else 'below'}
Positioning: {', '.join(ls1_positions)}
"""

# VT overview
if 'VT' in data.columns and latest_ma['VT_20d'] is not None:
    vt_status = "above" if signals['VT_20d'] else "below"
    vt_message = f"""
📊 FTSE Global All Cap (VT)
---------------------------
VT 20d MA: {vt_status} ({latest_ma['VT_20d']:.2f})
Latest Price: {latest_prices['VT']:.2f}
"""
else:
    vt_message = """
📊 FTSE Global All Cap (VT)
---------------------------
VT: data unavailable
"""

# Combine all messages
full_message = "\n".join([ls3_message, ls3_overview, ls2_message, ls1_message, vt_message])

# Send to NTFY
send_to_ntfy(full_message)

# Print for debugging
print(full_message)

import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import requests
import uuid

# ========= PUSH NOTIFICATIONS ========= #
def send_to_ntfy(message, topic="LSBot"):  # <-- replace with your topic
    url = f"https://ntfy.sh/{topic}"
    headers = {"Title": "Trading Signal"}
    requests.post(url, data=message.encode("utf-8"), headers=headers)

# ========= FETCH DATA ========= #
def fetch_data(tickers, period="2y"):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365*int(period.replace("y", "")))
    df = yf.download(tickers, start=start_date, end=end_date, progress=False, auto_adjust=True)["Close"]
    return df

def days_to_quarter_end(current_date):
    quarter_ends = [datetime(current_date.year, m, d) for m, d in [(3,31),(6,30),(9,30),(12,31)]]
    next_quarter = min([q for q in quarter_ends if q >= current_date], default=datetime(current_date.year+1, 3, 31))
    return (next_quarter - current_date).days

# ========= MAIN ========= #
def main():
    tickers = ["SPY", "QQQ", "IEF", "VT"]
    data = fetch_data(tickers)

    latest = data.iloc[-1]
    date_str = data.index[-1].strftime("%Y-%m-%d")
    days_left = days_to_quarter_end(data.index[-1])

    # Moving averages
    ma = {
        "SPY_20w": data["SPY"].rolling(100).mean().iloc[-1],
        "QQQ_20w": data["QQQ"].rolling(100).mean().iloc[-1],
        "SPY_200d": data["SPY"].rolling(200).mean().iloc[-1],
        "QQQ_220d": data["QQQ"].rolling(220).mean().iloc[-1],
        "IEF_50d": data["IEF"].rolling(50).mean().iloc[-1],
        "VT_20d": data["VT"].rolling(20).mean().iloc[-1],
    }

    # Signals
    signals = {
        "SPY_20w": latest["SPY"] > ma["SPY_20w"],
        "QQQ_20w": latest["QQQ"] > ma["QQQ_20w"],
        "SPY_200d": latest["SPY"] > ma["SPY_200d"],
        "QQQ_220d": latest["QQQ"] > ma["QQQ_220d"],
        "IEF_50d": latest["IEF"] > ma["IEF_50d"],
        "VT_20d": latest["VT"] > ma["VT_20d"],
    }

    # LS3.0 Implementation
    spy_band = (ma["SPY_200d"]*0.9825, ma["SPY_200d"]*1.0175)
    ief_band = (ma["IEF_50d"]*0.98, ma["IEF_50d"]*1.02)
    sig1 = "On" if latest["SPY"] > spy_band[1] else "Off" if latest["SPY"] < spy_band[0] else "On"
    sig2 = "On" if latest["IEF"] > ief_band[1] else "Off" if latest["IEF"] < ief_band[0] else "On"
    ls3_impl = "3LUS" if sig1=="On" and sig2=="On" else "Cash"

    # Messages
    ls3_impl_msg = f"**LS3.0 Impl.**\n- Signal1: {sig1}\n- Signal2: {sig2}\n- Positioning: {ls3_impl}"
    ls3_msg = f"**LS3.0**\n- SPX: {'above' if signals['SPY_200d'] else 'below'} 200d MA\n- IEF: {'above' if signals['IEF_50d'] else 'below'} 50d MA\n- Positioning: {'3LUS' if signals['SPY_200d'] and signals['IEF_50d'] else '3TYL' if signals['IEF_50d'] else 'Cash'}"
    ls2_msg = f"**LS2.0**\n- SPX: {'above' if signals['SPY_200d'] else 'below'} 200d MA\n- NDX: {'above' if signals['QQQ_220d'] else 'below'} 220d MA\n- IEF: {'above' if signals['IEF_50d'] else 'below'} 50d MA\n- Positioning: {', '.join([p for p in ['3LUS' if signals['SPY_200d'] else '', 'LQQ3' if signals['QQQ_220d'] else '', '3TYL' if signals['IEF_50d'] else '', 'Cash' if not any([signals['SPY_200d'],signals['QQQ_220d'],signals['IEF_50d']]) else ''] if p])}"
    ls1_msg = f"**LS1.0**\n- SPX: {'above' if signals['SPY_20w'] else 'below'} 20w MA\n- NDX: {'above' if signals['QQQ_20w'] else 'below'} 20w MA\n- Positioning: {', '.join([p for p in ['3LUS' if signals['SPY_20w'] else '', 'LQQ3' if signals['QQQ_20w'] else '', 'Cash' if not any([signals['SPY_20w'],signals['QQQ_20w']]) else ''] if p])}"
    vt_msg = f"**FTSE Global All Cap (VT)**\n- VT: {'above' if signals['VT_20d'] else 'below'} 20d MA ({ma['VT_20d']:.2f})\n- Price: {latest['VT']:.2f}"

    # Final message
    msg = f"📊 Trading Signals — {date_str}\nRun ID: {uuid.uuid4()}\nDays to Q-end: {days_left}\n\n{ls3_impl_msg}\n\n{ls3_msg}\n\n{ls2_msg}\n\n{ls1_msg}\n\n{vt_msg}"
    send_to_ntfy(msg)

if __name__ == "__main__":
    main()

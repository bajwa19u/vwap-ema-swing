"""Download ~2 years of 1h bars from Yahoo into research/cache/ (research only;
live signals use Alpaca). Usage: python research/fetch.py"""
from pathlib import Path
import yfinance as yf

UNIVERSE = ["SPY", "QQQ", "IWM", "NVDA", "TSLA", "AMD", "META", "AAPL", "MSFT",
            "AMZN", "GOOGL", "AVGO", "NFLX", "PLTR", "COIN", "MU", "MSTR", "SMCI",
            "UBER", "CRM", "SHOP", "HOOD", "ORCL", "JPM", "XOM", "LLY", "BA", "ARM"]
CACHE = Path(__file__).parent / "cache"


def main():
    CACHE.mkdir(exist_ok=True)
    for t in UNIVERSE:
        df = yf.download(t, period="729d", interval="1h", auto_adjust=False,
                         progress=False, prepost=False, multi_level_index=False)
        df.index = df.index.tz_convert("America/New_York")
        df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
        df.columns = ["open", "high", "low", "close", "volume"]
        df.to_pickle(CACHE / f"{t}.pkl")
        print(t, len(df), df.index[0].date(), df.index[-1].date())


if __name__ == "__main__":
    main()

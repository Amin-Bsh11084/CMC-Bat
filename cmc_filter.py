import os
import requests
import pandas as pd
from loguru import logger

logger.add("run_log.txt", rotation="1 MB")

BASE = "https://api.coingecko.com/api/v3/coins/markets"

# اگر خواستی 200 کوین بگیری، per_page=200. (حداکثر 250)
PARAMS = {
    "vs_currency": "usd",
    "order": "market_cap_desc",
    "per_page": 200,
    "page": 1,
    "sparkline": "false",
    "price_change_percentage": "1h,24h,7d"  # درصد تغییرات را یکجا می‌دهد
}

def fetch_markets():
    logger.info("📡 Fetching markets from CoinGecko...")
    r = requests.get(BASE, params=PARAMS, timeout=30)
    r.raise_for_status()
    data = r.json()
    logger.success(f"✅ Received {len(data)} records from CoinGecko")
    return data

def save_to_csv(data):
    rows = []
    for c in data:
        rows.append({
            "id": c.get("id"),
            "symbol": c.get("symbol"),
            "name": c.get("name"),
            "market_cap_rank": c.get("market_cap_rank"),
            "current_price": c.get("current_price"),
            "price_change_pct_1h": (c.get("price_change_percentage_1h_in_currency")),
            "price_change_pct_24h": (c.get("price_change_percentage_24h_in_currency")),
            "price_change_pct_7d": (c.get("price_change_percentage_7d_in_currency")),
            "market_cap": c.get("market_cap"),
            "total_volume": c.get("total_volume"),
            "circulating_supply": c.get("circulating_supply"),
            "total_supply": c.get("total_supply"),
            "ath": c.get("ath"),
            "atl": c.get("atl"),
            "last_updated": c.get("last_updated"),
        })
    df = pd.DataFrame(rows)
    os.makedirs("data", exist_ok=True)
    out = "data/gecko_markets.csv"
    df.to_csv(out, index=False, encoding="utf-8-sig")
    logger.success(f"💾 CSV saved: {out}")

def main():
    data = fetch_markets()
    save_to_csv(data)

if __name__ == "__main__":
    try:
        main()
        logger.info("🎯 Script finished successfully")
    except Exception as e:
        logger.exception(f"❌ Error: {e}")
        raise

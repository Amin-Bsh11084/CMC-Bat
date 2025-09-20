import os
import requests
import pandas as pd
from loguru import logger

# پیکربندی لاگ
logger.add("run_log.txt", rotation="1 MB")  # ذخیره لاگ‌ها در فایل محلی

# گرفتن API KEY از Secrets
API_KEY = os.getenv("CMC_API_KEY")
if not API_KEY:
    logger.error("❌ CMC_API_KEY not found in environment variables")
    raise ValueError("CMC_API_KEY not found")

# تنظیمات API
URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
PARAMS = {
    "start": "1",
    "limit": "200",   # تعداد کوین‌ها
    "convert": "USD"
}
HEADERS = {
    "Accepts": "application/json",
    "X-CMC_PRO_API_KEY": API_KEY
}

def fetch_listings():
    """دریافت داده از CoinMarketCap"""
    logger.info("📡 Fetching data from CoinMarketCap API...")
    response = requests.get(URL, headers=HEADERS, params=PARAMS)
    response.raise_for_status()
    data = response.json()["data"]
    logger.success(f"✅ Received {len(data)} records from API")
    return data

def save_to_csv(data):
    """ذخیره داده‌ها با ستون‌های مهم بازار"""
    rows = []
    for coin in data:
        rows.append({
            "id": coin["id"],
            "name": coin["name"],
            "symbol": coin["symbol"],
            "cmc_rank": coin["cmc_rank"],
            "price": coin["quote"]["USD"]["price"],
            "percent_change_1h": coin["quote"]["USD"]["percent_change_1h"],
            "percent_change_24h": coin["quote"]["USD"]["percent_change_24h"],
            "market_cap": coin["quote"]["USD"]["market_cap"],
            "volume_24h": coin["quote"]["USD"]["volume_24h"],
            "last_updated": coin["last_updated"]
        })

    df = pd.DataFrame(rows)
    os.makedirs("data", exist_ok=True)

    output_file = "data/cmc_output.csv"
    df.to_csv(output_file, index=False, encoding="utf-8-sig")
    logger.success(f"💾 CSV saved (replaced old file): {output_file}")

def main():
    listings = fetch_listings()
    save_to_csv(listings)

if __name__ == "__main__":
    try:
        main()
        logger.info("🎯 Script finished successfully")
    except Exception as e:
        logger.exception(f"❌ خطا در اجرای برنامه: {e}")
        exit(1)

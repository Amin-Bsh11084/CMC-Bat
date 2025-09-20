import os
import requests
import pandas as pd
from datetime import datetime
from loguru import logger

# پیکربندی لاگ
logger.add("run_log.txt", rotation="1 MB")  # ذخیره لاگ‌ها در فایل محلی هم

# گرفتن API KEY از Secrets
API_KEY = os.getenv("CMC_API_KEY")
if not API_KEY:
    logger.error("❌ CMC_API_KEY not found in environment variables")
    raise ValueError("CMC_API_KEY not found")

# تنظیمات API
URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
PARAMS = {
    "start": "1",
    "limit": "200",   # می‌تونی تغییر بدی
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
    """ذخیره داده‌ها داخل پوشه data"""
    df = pd.DataFrame(data)
    os.makedirs("data", exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y-%m-%d_%H-%M")
    output_file = f"data/output_{timestamp}.csv"
    df.to_csv(output_file, index=False)
    logger.success(f"💾 CSV saved: {output_file}")

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

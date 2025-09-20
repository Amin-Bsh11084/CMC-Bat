import os
import requests
import pandas as pd
from datetime import datetime

# گرفتن API KEY از Secrets
API_KEY = os.getenv("CMC_API_KEY")
if not API_KEY:
    raise ValueError("❌ CMC_API_KEY not found in environment variables")

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
    """دریافت داده از API"""
    response = requests.get(URL, headers=HEADERS, params=PARAMS)
    response.raise_for_status()
    data = response.json()["data"]
    return data

def save_to_csv(data):
    """ذخیره داده‌ها داخل پوشه data"""
    df = pd.DataFrame(data)
    os.makedirs("data", exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y-%m-%d_%H-%M")
    output_file = f"data/output_{timestamp}.csv"
    df.to_csv(output_file, index=False)
    print(f"✅ CSV saved: {output_file}")

def main():
    listings = fetch_listings()
    save_to_csv(listings)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ خطا در اجرای برنامه: {e}")
        exit(1)

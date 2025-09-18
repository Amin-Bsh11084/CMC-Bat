# cmc_filter.py
# -*- coding: utf-8 -*-

import os
import sys
import csv
import requests
from pathlib import Path

# -----------------------------
# تنظیمات اصلی
# -----------------------------
CMC_API_KEY = os.getenv("CMC_API_KEY")
LIMIT = int(os.getenv("CMC_LIMIT", "200"))     # تعداد ارزها
CONVERT = os.getenv("CMC_CONVERT", "USD")      # ارز مبنا
OUTPUT_PATH = os.getenv("CMC_OUTPUT", "data/cmc_list.csv")

LISTINGS_URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
INFO_URL = "https://pro-api.coinmarketcap.com/v2/cryptocurrency/info"

HEADERS = {"X-CMC_PRO_API_KEY": CMC_API_KEY}

# ستون‌های خروجی CSV (ترتیب همین‌طور می‌ماند)
CSV_FIELDS = [
    "id", "slug", "name", "symbol", "cmc_rank",
    "type", "platform_name", "token_address",
    "total_supply", "circulating_supply", "max_supply",
    "price", "market_cap",
    "volume_24h", "volume_change_24h",
    "percent_change_1h", "percent_change_24h", "percent_change_7d",
    "tags", "whitepaper_url",
    "date_added", "last_updated"
]


# -----------------------------
# توابع کمکی
# -----------------------------

def log(msg: str):
    print(msg, flush=True)


def fetch_listings(limit=LIMIT, convert=CONVERT):
    """گرفتن لیست ارزها از listings/latest"""
    params = {"start": 1, "limit": limit, "convert": convert}
    log("🔹 Requesting listings from CoinMarketCap...")
    r = requests.get(LISTINGS_URL, headers=HEADERS, params=params, timeout=40)
    log(f"   ↳ Status: {r.status_code}")
    r.raise_for_status()
    payload = r.json()
    data = payload.get("data", [])
    log(f"✅ Listings received. Count: {len(data)}")
    return data


def fetch_info_by_ids(id_list):
    """گرفتن اطلاعات تکمیلی (whitepaper/type/...) برای مجموعه‌ای از IDها در یک درخواست"""
    if not id_list:
        return {}
    ids = ",".join(map(str, id_list))
    params = {"id": ids}
    log("🔹 Requesting extra info (whitepaper/type) from CMC info endpoint...")
    r = requests.get(INFO_URL, headers=HEADERS, params=params, timeout=40)
    log(f"   ↳ Status: {r.status_code}")
    r.raise_for_status()
    payload = r.json()
    data = payload.get("data", {})
    log(f"✅ Info received for {len(data)} ids.")
    return data  # dict keyed by string id


def detect_type(listing_item, info_obj):
    """
    تعیین نوع: coin یا token
    - اگر از /info مقدار category داشته باشیم، همونو برمی‌گردونیم.
    - در غیر این صورت اگر platform خالی باشد: coin، وگرنه token.
    """
    if info_obj:
        cat = info_obj.get("category")
        if cat in ("coin", "token"):
            return cat

    platform = listing_item.get("platform")
    return "coin" if platform is None else "token"


def first_whitepaper_url(info_obj):
    """برگشت اولین لینک whitepaper اگر موجود بود"""
    if not info_obj:
        return ""
    urls = info_obj.get("urls") or {}
    tech_docs = urls.get("technical_doc") or []
    if tech_docs and isinstance(tech_docs, list):
        return tech_docs[0] or ""
    return ""


def stringify_tags(tags):
    """لیست تگ‌ها را با ; جدا می‌کند"""
    if not tags:
        return ""
    return ";".join([t for t in tags if t])


def ensure_output_dir(path: str):
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def build_row(item, extra_info):
    """ساخت یک ردیف برای CSV از دو منبع listings و info"""
    q = (item.get("quote") or {}).get(CONVERT, {})
    platform = item.get("platform") or {}
    info_obj = extra_info or {}

    row = {
        "id": item.get("id"),
        "slug": item.get("slug"),
        "name": item.get("name"),
        "symbol": item.get("symbol"),
        "cmc_rank": item.get("cmc_rank"),
        "type": detect_type(item, info_obj),
        "platform_name": platform.get("name") if platform else "",
        "token_address": platform.get("token_address") if platform else "",
        "total_supply": item.get("total_supply"),
        "circulating_supply": item.get("circulating_supply"),
        "max_supply": item.get("max_supply"),
        "price": q.get("price"),
        "market_cap": q.get("market_cap"),
        "volume_24h": q.get("volume_24h"),
        "volume_change_24h": q.get("volume_change_24h"),
        "percent_change_1h": q.get("percent_change_1h"),
        "percent_change_24h": q.get("percent_change_24h"),
        "percent_change_7d": q.get("percent_change_7d"),
        "tags": stringify_tags(item.get("tags")),
        "whitepaper_url": first_whitepaper_url(info_obj),
        "date_added": item.get("date_added"),
        "last_updated": item.get("last_updated"),
    }
    return row


def save_as_csv(rows, path=OUTPUT_PATH):
    """ذخیره‌ی ردیف‌ها به CSV (هر بار جایگزین فایل قبلی می‌شود)"""
    ensure_output_dir(path)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    log(f"💾 CSV saved: {path}  (rows: {len(rows)})")


# -----------------------------
# اجرای اصلی
# -----------------------------

def main():
    log("🚀 Starting CMC daily fetch → CSV")
    if not CMC_API_KEY:
        log("❌ ERROR: CMC_API_KEY is not set!")
        sys.exit(1)

    try:
        listings = fetch_listings(limit=LIMIT, convert=CONVERT)
        if not listings:
            log("⚠️ No listings received. Exiting.")
            sys.exit(0)

        id_list = [it.get("id") for it in listings if it.get("id") is not None]
        info_map = fetch_info_by_ids(id_list)  # dict keyed by string id

        rows = []
        for it in listings:
            _id = it.get("id")
            info_obj = info_map.get(str(_id)) if _id is not None else None
            rows.append(build_row(it, info_obj))

        save_as_csv(rows, OUTPUT_PATH)

        # چند لاگ جمع‌بندی
        n_coin = sum(1 for r in rows if r["type"] == "coin")
        n_token = len(rows) - n_coin
        with_wp = sum(1 for r in rows if r["whitepaper_url"])
        log(f"📊 Summary → coins: {n_coin}, tokens: {n_token}, with whitepaper: {with_wp}")
        log("🎯 Done.")

    except requests.HTTPError as e:
        # خطاهای مرتبط با API (مثلاً 401/403/429/5xx)
        try:
            body = e.response.json()
        except Exception:
            body = {"message": str(e)}
        log(f"❌ HTTPError: {e} | Body: {body}")
        sys.exit(1)
    except Exception as e:
        log(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

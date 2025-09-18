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
LIMIT = 200
CONVERT = "USD"
OUTPUT_PATH = "data/cmc_list.csv"

LISTINGS_URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
INFO_URL = "https://pro-api.coinmarketcap.com/v2/cryptocurrency/info"

HEADERS = {"X-CMC_PRO_API_KEY": CMC_API_KEY}

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
    params = {"start": 1, "limit": limit, "convert": convert}
    log("🔹 Requesting listings...")
    r = requests.get(LISTINGS_URL, headers=HEADERS, params=params, timeout=40)
    log(f"   ↳ Status: {r.status_code}")
    r.raise_for_status()
    data = r.json().get("data", [])
    log(f"✅ Listings received: {len(data)}")
    return data

def fetch_info_by_ids(id_list):
    if not id_list:
        return {}
    ids = ",".join(map(str, id_list))
    params = {"id": ids}
    log("🔹 Requesting extra info (whitepaper/type)...")
    r = requests.get(INFO_URL, headers=HEADERS, params=params, timeout=40)
    log(f"   ↳ Status: {r.status_code}")
    r.raise_for_status()
    return r.json().get("data", {})

def detect_type(listing_item, info_obj):
    if info_obj and "category" in info_obj:
        return info_obj.get("category")
    return "coin" if listing_item.get("platform") is None else "token"

def first_whitepaper_url(info_obj):
    if not info_obj:
        return ""
    urls = info_obj.get("urls") or {}
    docs = urls.get("technical_doc") or []
    if docs and isinstance(docs, list):
        return docs[0] or ""
    return ""

def stringify_tags(tags):
    return ";".join(tags) if tags else ""

def ensure_output_dir(path: str):
    Path(path).parent.mkdir(parents=True, exist_ok=True)

def build_row(item, extra_info):
    q = (item.get("quote") or {}).get(CONVERT, {})
    platform = item.get("platform") or {}
    info_obj = extra_info or {}

    return {
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

def save_as_csv(rows, path=OUTPUT_PATH):
    ensure_output_dir(path)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    log(f"💾 CSV saved: {path} (rows: {len(rows)})")

# -----------------------------
# اجرای اصلی
# -----------------------------
def main():
    log("🚀 Starting CMC daily fetch → CSV")
    if not CMC_API_KEY:
        log("❌ ERROR: CMC_API_KEY is not set!")
        sys.exit(1)

    try:
        listings = fetch_listings()
        ids = [it.get("id") for it in listings if it.get("id")]
        info_map = fetch_info_by_ids(ids)

        rows = [build_row(it, info_map.get(str(it.get("id")))) for it in listings]
        save_as_csv(rows)

        n_coin = sum(1 for r in rows if r["type"] == "coin")
        n_token = len(rows) - n_coin
        with_wp = sum(1 for r in rows if r["whitepaper_url"])
        log(f"📊 Summary → coins: {n_coin}, tokens: {n_token}, with whitepaper: {with_wp}")
        log("🎯 Done.")

    except requests.HTTPError as e:
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

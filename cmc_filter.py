# cmc_filter.py
# -*- coding: utf-8 -*-
# CoinMarketCap Filter — 5 شرط کاربر
# -----------------------------------
# این اسکریپت با استفاده از API رسمی CoinMarketCap داده‌ها را می‌گیرد و طبق شروط زیر فیلتر می‌کند:
#   1) total_supply < 100,000,000,000 (صد میلیارد)
#   2) داشتن whitepaper (technical_doc)
#   3) نوع دارایی: coin / token / هر دو (قابل تنظیم)
#   4) cmc_rank < 1000
#   5) حجم معاملات 24ساعت بزرگ‌تر از حداقل تعیین‌شده و 'volume_change_24h' مثبت (> 0)
#
# نحوه استفاده:
#   - Python 3.9+ و کتابخانه requests لازم است:   pip install requests
#   - کلید API خود را در متغیر API_KEY قرار دهید (یا ENV: CMC_API_KEY)
#   - سپس اجرا کنید:  python cmc_filter.py
#
# خروجی:
#   - چاپ خلاصه 20 مورد اول
#   - ذخیره همه نتایج فیلترشده در فایل CSV: filtered_coins.csv
#
# نکات:
#   - endpoint ها: /v1/cryptocurrency/listings/latest و /v2/cryptocurrency/info
#   - برای تشخیص coin vs token از فیلد 'platform' استفاده می‌کنیم (None = coin, مقداردار = token).
#   - برای whitepaper از 'urls' → 'technical_doc' در /v2/cryptocurrency/info استفاده می‌کنیم.
#   - فیلد 'volume_change_24h' در 'quote' موجود است.
#
import os
import csv
import time
import requests
from typing import Dict, List, Any, Optional

API_KEY = os.getenv("CMC_API_KEY", "937955e4-a3d0-4b5f-8efb-9f171f29b271")  # ← کلیدت را اینجا بگذار یا ENV را تنظیم کن
BASE_URL = "https://pro-api.coinmarketcap.com"

# ---------- پیکربندی فیلترها ----------
LIMIT = 200  # چند ارز اول را بررسی کنیم
CONVERT = "USD"

# نوع دارایی: 'coin' یا 'token' یا 'any'
TYPE_FILTER = "any"

# شروط اصلی
MAX_TOTAL_SUPPLY = 100_000_000_000  # < 100B
MAX_RANK = 1000
REQUIRE_WHITEPAPER = True

# شرط حجم و روند
MIN_VOLUME_24H = 10_000_000  # حداقل 10M USD (قابل تغییر)
REQUIRE_VOLUME_UP = True      # volume_change_24h > 0

# ---------- توابع کمکی ----------
def _headers():
    return {
        "Accepts": "application/json",
        "X-CMC_PRO_API_KEY": API_KEY,
    }

def fetch_listings(limit: int = 200, convert: str = "USD") -> List[Dict[str, Any]]:
    """
    /v1/cryptocurrency/listings/latest
    برمی‌گرداند: لیست ارزها با فیلدهای بازار از جمله quote[convert].volume_24h و volume_change_24h.
    """
    url = f"{BASE_URL}/v1/cryptocurrency/listings/latest"
    params = {
        "start": 1,
        "limit": limit,
        "convert": convert,
        # "aux": "volume_change_24h",  # معمولاً نیازی نیست؛ طبق مستندات این فیلد موجود است.
    }
    r = requests.get(url, headers=_headers(), params=params, timeout=30)
    r.raise_for_status()
    payload = r.json()
    status = payload.get("status", {})
    if status.get("error_code"):
        raise RuntimeError(f"CMC error {status.get('error_code')}: {status.get('error_message')}")
    return payload.get("data", [])

def chunked(iterable, size):
    for i in range(0, len(iterable), size):
        yield iterable[i:i+size]

def fetch_info_by_ids(ids: List[int]) -> Dict[int, Dict[str, Any]]:
    """
    /v2/cryptocurrency/info
    - برای هر ID، metadata شامل urls.technical_doc (whitepaper) را برمی‌گرداند.
    - تا 1000 ID در یک درخواست. برای احتیاط بَچ 100تایی استفاده می‌کنیم.
    """
    info_map: Dict[int, Dict[str, Any]] = {}
    url = f"{BASE_URL}/v2/cryptocurrency/info"
    for batch in chunked(ids, 100):
        params = {"id": ",".join(str(x) for x in batch)}
        r = requests.get(url, headers=_headers(), params=params, timeout=30)
        r.raise_for_status()
        payload = r.json()
        status = payload.get("status", {})
        if status.get("error_code"):
            raise RuntimeError(f"CMC error {status.get('error_code')}: {status.get('error_message')}")
        data = payload.get("data", {})
        # data: dict keyed by stringified id
        for k, v in data.items():
            try:
                info_map[int(k)] = v
            except Exception:
                continue
        # برای رعایت ریتم ریکوئست‌ها (rate limit) اگر لازم شد کمی صبر:
        time.sleep(0.2)
    return info_map

def is_coin(item: Dict[str, Any]) -> bool:
    # platform == None → coin
    return item.get("platform") is None

def is_token(item: Dict[str, Any]) -> bool:
    return item.get("platform") is not None

def pick_supply(item: Dict[str, Any]) -> Optional[float]:
    # اول total_supply، بعد max_supply، در غیر این صورت None (رد می‌شود)
    total_supply = item.get("total_supply")
    if total_supply is not None:
        return float(total_supply)
    max_supply = item.get("max_supply")
    if max_supply is not None:
        return float(max_supply)
    return None

def has_whitepaper(info: Dict[str, Any]) -> bool:
    urls = (info or {}).get("urls", {})
    # CMC returns 'technical_doc' (array). بعضی پروژه‌ها ممکن است 'whitepaper' هم داشته باشند.
    technical_doc = urls.get("technical_doc") or urls.get("whitepaper")
    return bool(technical_doc and len(technical_doc) > 0 and str(technical_doc[0]).strip())

def filter_items(items: List[Dict[str, Any]], info_by_id: Dict[int, Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for it in items:
        try:
            coin_id = it["id"]
            name = it["name"]
            symbol = it["symbol"]
            rank = it.get("cmc_rank") or 10**9
            q = (it.get("quote") or {}).get(CONVERT, {})

            # نوع
            if TYPE_FILTER == "coin" and not is_coin(it):
                continue
            if TYPE_FILTER == "token" and not is_token(it):
                continue

            # رتبه
            if not (isinstance(rank, int) or isinstance(rank, float)) or rank >= MAX_RANK:
                continue

            # عرضه
            supply = pick_supply(it)
            if supply is None or supply >= MAX_TOTAL_SUPPLY:
                continue

            # حجم و روند
            vol = float(q.get("volume_24h") or 0.0)
            vchg = q.get("volume_change_24h")  # ممکن است None باشد
            if vol < MIN_VOLUME_24H:
                continue
            if REQUIRE_VOLUME_UP and (vchg is None or float(vchg) <= 0):
                continue

            # وایت‌پیپر
            if REQUIRE_WHITEPAPER:
                info = info_by_id.get(coin_id, {})
                if not has_whitepaper(info):
                    continue

            out.append({
                "id": coin_id,
                "rank": rank,
                "name": name,
                "symbol": symbol,
                "type": "coin" if is_coin(it) else "token",
                "total_supply": supply,
                "market_cap": q.get("market_cap"),
                "volume_24h": vol,
                "volume_change_24h_pct": vchg,
                "price": q.get("price"),
                "slug": it.get("slug"),
            })
        except Exception:
            # اگر چیزی خراب بود، از آن مورد عبور کن
            continue
    # مرتب‌سازی بر اساس rank و بعد حجم
    out.sort(key=lambda x: (x["rank"], -(x["volume_24h"] or 0)))
    return out

def save_csv(rows: List[Dict[str, Any]], path: str = "filtered_coins.csv"):
    if not rows:
        print("⚠️ هیچ نتیجه‌ای با شروط تعیین‌شده پیدا نشد.")
        return
    keys = ["rank","name","symbol","type","price","market_cap","volume_24h","volume_change_24h_pct","total_supply","id","slug"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in keys})
    print(f"✅ {len(rows)} رکورد ذخیره شد → {path}")

def main():
    if not API_KEY or API_KEY == "YOUR_API_KEY_HERE":
        raise SystemExit("❌ API Key تنظیم نشده. متغیر CMC_API_KEY یا مقدار API_KEY را پر کنید.")
    print("↪️ دریافت لیست‌ها از CoinMarketCap ...")
    listings = fetch_listings(limit=LIMIT, convert=CONVERT)
    ids = [it["id"] for it in listings if isinstance(it.get("id"), int)]
    print(f"— دریافت metadata برای {len(ids)} نماد ...")
    info_by_id = fetch_info_by_ids(ids)
    print("— اعمال فیلترها ...")
    rows = filter_items(listings, info_by_id)
    # چاپ 20 مورد اول
    for r in rows[:20]:
        # بعضی قیمت‌ها بسیار کوچک هستند؛ نمایش با 6 رقم اعشار
        price = r['price']
        price_str = f"{price:.6f}" if isinstance(price, (int, float)) else str(price)
        vchg = r['volume_change_24h_pct']
        vchg_str = f"{vchg:.2f}" if isinstance(vchg, (int, float)) else str(vchg)
        supply = r['total_supply']
        supply_str = f"{int(supply)}" if isinstance(supply, (int, float)) else str(supply)
        print(f"{int(r['rank'])}. {r['name']} ({r['symbol']}) | {r['type']} | Price: {price_str} | Vol24h: {r['volume_24h']:.0f} | VolChg24h%: {vchg_str} | Supply: {supply_str}")
    save_csv(rows)

if __name__ == "__main__":
    main()

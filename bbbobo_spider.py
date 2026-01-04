import json
import os
import time
import site_pokemy
from urllib.parse import urlencode
import requests
from bs4 import BeautifulSoup

# ======= 請改成你自己的 =======
BOT_TOKEN = "8576804966:AAFf8BkEOaHrYRHJ1iRKlN1aWNYhMtYcw1k"
CHAT_ID = 5584187517
# ============================

BASE_URL = "https://www.bbbobo.com.tw/shop/0/Goods_List.asp"
KEYWORDS = ["相機", "記憶卡"]
SEEN_FILE = "seen_items.json"

def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            try:
                return set(json.load(f))
            except Exception:
                return set()
    return set()

def save_seen(seen):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(list(seen), f, ensure_ascii=False, indent=2)

def fetch_page(keyword, page=None):
    params = {
        "KeyWord": keyword,
        "SearchZone": 0,
        "SelectArea": 0,
        "SelectAgent": 0,
        "MinM": "",
        "MaxM": "",
    }
    if page is not None and page > 1:
        params["Page"] = page
    url = f"{BASE_URL}?{urlencode(params, doseq=True)}"
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    return resp.text

def parse_items(html):
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for li in soup.select("div.goods-list-info li"):
        info = li.select_one("div.pr-info")
        sim = li.select_one("div.siminfo")
        if not info or not sim:
            continue
        gid = info.get("gid") or info.get("itemid")
        if not gid:
            continue
        
        shop_div = sim.select_one("div.shop-name")
        shop = shop_div.get_text(strip=True) if shop_div else ""
        
        name_div = sim.select_one("div.pr-name")
        title = name_div.get_text(strip=True) if name_div else ""
        
        price_span = li.select_one("span.pr-price-org")
        price = price_span.get_text(strip=True) if price_span else ""
        
        link = "https://www.bbbobo.com.tw"
        aid = info.get("aid")
        if aid and gid:
            link = f"https://www.bbbobo.com.tw/shop/0/Goods.asp?AID={aid}&GID={gid}"
        
        img_tag = info.select_one("img")
        img_src = ""
        if img_tag and img_tag.get("src"):
            src = img_tag["src"]
            if src.startswith("http"):
                img_src = src
            else:
                img_src = "https://www.bbbobo.com.tw/" + src.lstrip("/")
        
        items.append({
            "gid": gid,
            "title": title,
            "price": price,
            "shop": shop,
            "link": link,
            "img": img_src,
        })
    return items

def crawlkeyword(keyword, maxpages=50):
    allitems = []
    page = 1
    all_seen_gids = set()
    
    while page <= maxpages:
        html = fetch_page(keyword, page=page)
        items = parse_items(html)
        print(f"{keyword} 第 {page} 頁 {len(items)} 個商品")
        
        if not items:
            break
        
        newinthispage = []
        for it in items:
            gid = it['gid']
            if gid not in all_seen_gids:
                all_seen_gids.add(gid)
                newinthispage.append(it)
        
        if not newinthispage:
            break
        
        allitems.extend(newinthispage)
        page += 1
        time.sleep(1)
    
    return allitems

def send_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    resp = requests.post(url, data=payload, timeout=15)
    resp.raise_for_status()

def send_photo(caption, photo_url):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    payload = {
        "chat_id": CHAT_ID,
        "photo": photo_url,
        "caption": caption,
        "parse_mode": "HTML",
    }
    resp = requests.post(url, data=payload, timeout=15)
    resp.raise_for_status()

def main():
    seen = load_seen()
    new_items = []

    # 1. bbbobo 部分
    for kw in KEYWORDS:
        items = crawlkeyword(kw, maxpages=50)
        print(kw, "抓到商品數：", len(items))
        
        for it in items:
            # 只保留標題包含關鍵字的商品
            if kw not in it['title']:
                continue
            
            key = f"{kw}_{it['gid']}"
            if key not in seen:
                seen.add(key)
                it["keyword"] = kw
                new_items.append(it)

    # 2. pokemy 部分
    for kw in KEYWORDS:
        items = site_pokemy.crawl_keyword(kw)
        print("pokemy", kw, "抓到商品數：", len(items))
        
        for it in items:
            # 只保留標題包含關鍵字的商品
            if kw not in it['title']:
                continue
            
            key = f"pokemy_{kw}_{it['gid']}"
            if key not in seen:
                seen.add(key)
                new_items.append(it)

    save_seen(seen)

    if not new_items:
        send_telegram("今天沒有新的『相機／記憶卡』商品（bbbobo + pokemy）。")
        return

    for it in new_items:
        caption = (
            f"[{it.get('site','')}] [{it['keyword']}] {it['title']} {it['price']}\n"
            f"店鋪：{it.get('shop', '')}\n"
            f"{it['link']}"
        )
        img_url = it.get("img", "")
        if img_url.startswith("http://") or img_url.startswith("https://"):
            try:
                send_photo(caption, img_url)
            except Exception as e:
                print("send_photo 失敗，改用文字：", e)
                send_telegram(caption)
        else:
            send_telegram(caption)
        time.sleep(0.5)

if __name__ == "__main__":
    main()

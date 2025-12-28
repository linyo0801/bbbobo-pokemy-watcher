import requests
from bs4 import BeautifulSoup


BASE_URL = "http://pokemy.tw/Home/PostCommodity"


def fetch_page(keyword: str) -> str:
    """
    用 POST 送 keyword，取得搜尋結果頁 HTML。
    """
    data = {
        "keyword": keyword,
    }
    # pokemy 是表單送出，因此用 POST
    resp = requests.post(BASE_URL, data=data, timeout=15)
    resp.raise_for_status()
    return resp.text


def parse_items(html: str, keyword: str):
    """
    解析 pokemy 搜尋結果，回傳統一格式的商品列表。
    欄位：site, gid(編號), title(品名), price(售價), shop, link, img(data URL)
    """
    soup = BeautifulSoup(html, "html.parser")
    items = []

    for div in soup.select("div#posts div.item"):
        # 圖片（data:image base64）
        a_img = div.select_one("a[href^='data:image']")
        img_src = a_img.get("href", "") if a_img else ""

        # 描述文字區塊（含 編號/品名/售價/數量）
        span = div.select_one("span[style*='font-size']")
        text = span.get_text("\n", strip=True) if span else ""

        gid = ""
        title = ""
        price = ""

        # 粗暴拆行
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("編號："):
                gid = line.replace("編號：", "").strip()
            elif line.startswith("品名："):
                title = line.replace("品名：", "").strip()
            elif line.startswith("售價："):
                price = line.replace("售價：", "").strip()

        if not gid and not title:
            continue

        items.append(
            {
                "site": "pokemy",
                "gid": gid or title,
                "title": title,
                "price": price,
                "shop": "寶可賣 PoKeMy",
                "link": BASE_URL,
                "img": img_src,
                "keyword": keyword,
            }
        )

    return items


def crawl_keyword(keyword: str):
    """
    給主程式用：crawl_keyword("相機") -> List[dict]
    """
    html = fetch_page(keyword)
    return parse_items(html, keyword)

import requests
from bs4 import BeautifulSoup
import datetime
import os
import time

# 한글 매핑 DB
KOR_MAP = {
    "his-hers": "히스 앤 허스",
    "people-we-meet-on-vacation": "우리의 열 번째 여름",
    "the-ugly": "얼굴",
    "your-letter": "연의 편지",
    "the-great-flood": "대홍수",
    "tron-ares": "트론: 아레스",
    "avatar-the-way-of-water": "아바타: 물의 길"
}

def fetch_data(platform, loc="world", limit=10):
    url = f"https://flixpatrol.com/top10/{platform}/{loc}/today/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    
    try:
        res = requests.get(url, headers=headers, timeout=20)
        soup = BeautifulSoup(res.text, 'html.parser')
        rows = soup.select('tr.table-group')
        data = []
        
        for row in rows[:limit]:
            tds = row.find_all('td')
            if len(tds) < 3: continue
            
            # 1. 제목 추출 (텍스트가 없으면 URL에서 추출)
            title_link = row.find('a', href=True)
            if title_link and '/title/' in title_link['href']:
                raw_slug = title_link['href'].split('/')[-2]
                title_clean = raw_slug.replace('-', ' ').title()
                kor_title = KOR_MAP.get(raw_slug, title_clean)
            else:
                kor_title = "Unknown Title"
                title_clean = "Unknown"

            # 2. 순위 및 변동 (패턴 분석)
            rank = tds[0].get_text(strip=True).replace(".", "")
            change = "-"
            for span in row.find_all('span'):
                txt = span.get_text(strip=True)
                if any(x in txt for x in ['▲', '▼', 'n/a']):
                    change = txt.replace('n/a', '신규')
                    break
            
            # 3. 점수 및 기간 (데이터 성격별 분류)
            idx, days = "0", "-"
            for td in tds:
                txt = td.get_text(strip=True)
                if ' d' in txt: days = txt
                elif txt.isdigit() and int(txt) > 50: idx = txt

            data.append({"rank": rank, "change": change, "title": kor_title, "eng": title_clean, "idx": idx, "days": days})
        return data
    except:
        return []

def format_section(cfg):
    msg = f"🎬 **{cfg['name']}**\n"
    
    # 글로벌 리포트
    world = fetch_data(cfg['id'], "world", cfg.get('lim', 10))
    if world:
        msg += f" 🌎 **글로벌 TOP {len(world)}**\n\n"
        for i in world:
            msg += f" {i['rank']}. {i['title']} | {i['idx']} ┃ {i['change']} ┃ {i['days']}\n"
    
    # 한국 리포트
    if cfg.get('korea'):
        korea = fetch_data(cfg['id'], "south-korea", 10)
        if korea:
            msg += f"\n 🇰🇷 **한국 TOP 10**\n\n"
            for i in korea:
                msg += f" {i['rank']}. {i['title']} ({i['eng']}) | {i['idx']} ┃ {i['change']} ┃ {i['days']}\n"
    return msg + "\n"

def send_telegram(text):
    token, chat_id = os.environ.get("TELEGRAM_TOKEN"), os.environ.get("CHAT_ID")
    if token and chat_id:
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", 
                      json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})

def main():
    now = datetime.datetime.now().strftime("%y.%m.%d %H:%M")
    m1 = f"🏆 **OTT 통합 랭킹 [1/2] ({now})**\n━━━━━━━━━━━━━━━━━━\n\n"
    m1 += format_section({"id": "netflix", "name": "NETFLIX", "korea": True})
    m1 += format_section({"id": "disney", "name": "DISNEY+", "korea": True})
    send_telegram(m1)
    
    time.sleep(2)
    
    m2 = f"🏆 **OTT 통합 랭킹 [2/2] ({now})**\n━━━━━━━━━━━━━━━━━━\n\n"
    for p in [{"id": "apple-tv", "name": "APPLE TV+", "lim": 5}, {"id": "amazon-prime", "name": "AMAZON", "lim": 5}, {"id": "hbo", "name": "HBO MAX", "lim": 5}]:
        m2 += format_section(p)
    send_telegram(m2)

if __name__ == "__main__":
    main()

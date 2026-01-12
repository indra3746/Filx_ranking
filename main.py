import requests
from bs4 import BeautifulSoup
import datetime
import os
import time

# 한글 매핑 DB
KOR_MAP = {
    "His & Hers": "히스 앤 허스",
    "People We Meet on Vacation": "우리의 열 번째 여름",
    "The Ugly": "얼굴",
    "Your Letter": "연의 편지",
    "The Great Flood": "대홍수",
    "TRON: Ares": "트론: 아레스",
    "Avatar: The Way of Water": "아바타: 물의 길"
}

def fetch_data(platform, loc="world", limit=10):
    url = f"https://flixpatrol.com/top10/{platform}/{loc}/today/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        res = requests.get(url, headers=headers, timeout=20)
        soup = BeautifulSoup(res.text, 'html.parser')
        rows = soup.select('tr.table-group')
        data = []
        
        for row in rows[:limit]:
            tds = row.find_all('td')
            if len(tds) < 3: continue
            
            # 1. 순위 및 변동 (앞쪽 열)
            rank = tds[0].get_text(strip=True).replace(".", "")
            change = "-"
            change_span = tds[1].select_one('span')
            if change_span:
                change = change_span.get_text(strip=True).replace('n/a', '신규')
            
            # 2. 제목, 점수, 기간 동적 분류
            temp_title, temp_idx, temp_days = "", "0", "-"
            
            for td in tds:
                txt = td.get_text(strip=True)
                if not txt: continue
                
                # ' d'가 포함되면 기간
                if ' d' in txt:
                    temp_days = txt
                # 순수한 숫자이고 50보다 크면 점수(Index)로 간주
                elif txt.isdigit() and int(txt) > 50:
                    temp_idx = txt
                # 링크(a)가 포함되어 있거나 텍스트가 긴 경우 제목으로 간주
                elif td.find('a') or (not txt.isdigit() and len(txt) > 1):
                    if not temp_title: # 첫 번째로 발견된 유효 텍스트를 제목으로
                        temp_title = txt

            kor_title = KOR_MAP.get(temp_title, temp_title)
            data.append({"rank": rank, "change": change, "title": kor_title, "eng": temp_title, "idx": temp_idx, "days": temp_days})
            
        return data
    except Exception as e:
        print(f"Error: {e}")
        return []

def format_section(cfg):
    msg = f"🎬 **{cfg['name']}**\n"
    
    # 글로벌 섹션
    world = fetch_data(cfg['id'], "world", cfg.get('lim', 10))
    if world:
        msg += f" 🌎 **글로벌 TOP {len(world)}**\n\n"
        for i in world:
            msg += f" {i['rank']}. {i['title']} | {i['idx']} ┃ {i['change']} ┃ {i['days']}\n"
    
    # 한국 섹션
    if cfg.get('korea'):
        korea = fetch_data(cfg['id'], "south-korea", 10)
        if korea:
            msg += f"\n 🇰🇷 **한국 TOP 10**\n\n"
            for i in korea:
                msg += f" {i['rank']}. {i['title']} ({i['eng']}) | {i['idx']} ┃ {i['change']} ┃ {i['days']}\n"
    return msg + "\n"

def send_telegram(text):
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("CHAT_ID")
    if token and chat_id:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})

def main():
    now = datetime.datetime.now().strftime("%y.%m.%d %H:%M")
    
    m1 = f"🏆 **OTT 통합 랭킹 [1/2] ({now})**\n━━━━━━━━━━━━━━━━━━\n\n"
    m1 += format_section({"id": "netflix", "name": "NETFLIX", "korea": True})
    m1 += format_section({"id": "disney", "name": "DISNEY+", "korea": True})
    send_telegram(m1)
    
    time.sleep(2)
    
    m2 = f"🏆 **OTT 통합 랭킹 [2/2] ({now})**\n━━━━━━━━━━━━━━━━━━\n\n"
    for p in [{"id": "apple-tv", "name": "APPLE TV+", "lim": 5}, 
              {"id": "amazon-prime", "name": "AMAZON", "lim": 5}, 
              {"id": "hbo", "name": "HBO MAX", "lim": 5}]:
        m2 += format_section(p)
    send_telegram(m2)

if __name__ == "__main__":
    main()

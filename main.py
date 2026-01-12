import requests
from bs4 import BeautifulSoup
import datetime
import os
import time

# 한글 매핑 데이터베이스
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
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        rows = soup.select('tr.table-group')
        data = []
        
        for row in rows[:limit]:
            # 1. 제목 추출 (클래스명 타겟팅으로 점수 섞임 방지)
            title_td = row.find('td', class_='table-main')
            if not title_td: continue
            eng_title = title_td.get_text(strip=True)
            kor_title = KOR_MAP.get(eng_title, eng_title)
            
            # 2. 순위 (첫 번째 열)
            rank = row.find_all('td')[0].get_text(strip=True).replace(".", "")
            
            # 3. 변동 (두 번째 열 span)
            change = "-"
            change_td = row.find_all('td')[1]
            change_span = change_td.select_one('span')
            if change_span:
                change = change_span.get_text(strip=True).replace('n/a', '신규')
            
            # 4. 점수(Index)와 기간(Days) - 텍스트 패턴으로 찾기
            idx = "0"
            days = "-"
            for td in row.find_all('td'):
                txt = td.get_text(strip=True)
                if txt.isdigit() and int(txt) > 50: # 보통 50점 이상을 점수로 간주
                    idx = txt
                if ' d' in txt: # '4 d' 같은 형태 찾기
                    days = txt

            data.append({"rank": rank, "change": change, "title": kor_title, "eng": eng_title, "idx": idx, "days": days})
        return data
    except:
        return []

def format_section(cfg):
    msg = f"🎬 **{cfg['name']}**\n"
    
    # 글로벌 리스트
    world = fetch_data(cfg['id'], "world", cfg.get('lim', 10))
    if world:
        msg += f" 🌎 **글로벌 TOP {len(world)}**\n\n"
        for i in world:
            msg += f" {i['rank']}. {i['title']} | {i['idx']} ┃ {i['change']} ┃ {i['days']}\n"
    
    # 한국 리스트
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
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", 
                      json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})

if __name__ == "__main__":
    now = datetime.datetime.now().strftime("%y.%m.%d %H:%M")
    m1 = f"🏆 **OTT 통합 랭킹 [1/2] ({now})**\n━━━━━━━━━━━━━━━━━━\n\n"
    m1 += format_section({"id": "netflix", "name": "NETFLIX", "korea": True})
    m1 += format_section({"id": "disney", "name": "DISNEY+", "korea": True})
    send_telegram(m1)
    
    time.sleep(1)
    
    m2 = f"🏆 **OTT 통합 랭킹 [2/2] ({now})**\n━━━━━━━━━━━━━━━━━━\n\n"
    for p in [{"id": "apple-tv", "name": "APPLE TV+", "lim": 5}, 
              {"id": "amazon-prime", "name": "AMAZON", "lim": 5}, 
              {"id": "hbo", "name": "HBO MAX", "lim": 5}]:
        m2 += format_section(p)
    send_telegram(m2)

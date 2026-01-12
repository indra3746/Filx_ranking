import requests
from bs4 import BeautifulSoup
import datetime
import os
import time

# 한글 제목 매핑 (실제 데이터 기반 업데이트)
KOR_MAP = {
    "HIS & HERS": "히스 앤 허스",
    "People We Meet on Vacation": "우리의 열 번째 여름",
    "The Ugly": "얼굴",
    "Your Letter": "연의 편지",
    "The Great Flood": "대홍수",
    "TRON: Ares": "트론: 아레스",
    "Avatar: The Way of Water": "아바타: 물의 길",
    "Culinary Class Wars": "흑백요리사",
    "Stranger Things": "기묘한 이야기"
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
            tds = row.find_all('td')
            if len(tds) < 3: continue
            
            # 1. 순위 및 변동
            rank = tds[0].get_text(strip=True).replace(".", "")
            change = "-"
            change_span = tds[1].select_one('span')
            if change_span:
                change = change_span.get_text(strip=True).replace('n/a', '신규')
            
            # 2. 제목 (핵심: a 태그 내부 텍스트만 추출하여 점수와 섞이지 않게 함)
            title_tag = tds[2].find('a')
            eng_title = title_tag.get_text(strip=True) if title_tag else tds[2].get_text(strip=True)
            kor_title = KOR_MAP.get(eng_title, eng_title)
            
            # 3. 점수(Index)와 기간(Days)
            idx = tds[3].get_text(strip=True)
            # ' d'가 포함된 열을 찾아 기간(days) 정보 추출
            days = "-"
            for td in tds:
                txt = td.get_text(strip=True)
                if ' d' in txt:
                    days = txt
                    break

            data.append({"rank": rank, "change": change, "title": kor_title, "eng": eng_title, "idx": idx, "days": days})
        return data
    except:
        return []

def format_section(cfg):
    msg = f"🎬 **{cfg['name']}**\n"
    
    # 글로벌 TOP (d 표시)
    world = fetch_data(cfg['id'], "world", cfg.get('lim', 10))
    if world:
        msg += f" 🌎 **글로벌 TOP {len(world)}**\n\n"
        for i in world:
            msg += f" {i['rank']}. {i['title']} | {i['idx']} ┃ {i['change']} ┃ {i['days']}\n"
    
    # 한국 TOP (d 표시)
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
    
    # 메시지 분할 전송
    m1 = f"🏆 **OTT 통합 랭킹 [1/2] ({now})**\n━━━━━━━━━━━━━━━━━━\n\n"
    m1 += format_section({"id": "netflix", "name": "NETFLIX", "korea": True})
    m1 += format_section({"id": "disney", "name": "DISNEY+", "korea": True})
    send_telegram(m1)
    
    time.sleep(1) # 안정적인 전송을 위한 간격
    
    m2 = f"🏆 **OTT 통합 랭킹 [2/2] ({now})**\n━━━━━━━━━━━━━━━━━━\n\n"
    for p in [{"id": "apple-tv", "name": "APPLE TV+", "lim": 5}, 
              {"id": "amazon-prime", "name": "AMAZON", "lim": 5}, 
              {"id": "hbo", "name": "HBO MAX", "lim": 5}]:
        m2 += format_section(p)
    send_telegram(m2)

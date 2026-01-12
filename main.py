import requests
from bs4 import BeautifulSoup
import datetime
import os
import time

# 한글 매핑 딕셔너리
KOR_MAP = {
    "His & Hers": "히스 앤 허스",
    "People We Meet on Vacation": "우리의 열 번째 여름",
    "The Ugly": "얼굴",
    "Your Letter": "연의 편지",
    "The Great Flood": "대홍수",
    "TRON: Ares": "트론: 아레스",
    "Avatar: The Way of Water": "아바타: 물의 길"
}

def fetch_simple_ranking(platform, loc="world", limit=10):
    url = f"https://flixpatrol.com/top10/{platform}/{loc}/today/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        rows = soup.select('tr.table-group')
        parsed = []
        for row in rows[:limit]:
            tds = row.find_all('td')
            if len(tds) < 3: continue
            
            # 순위 숫자만 추출하여 '위' 붙이기
            rank_num = tds[0].get_text(strip=True).replace(".", "")
            rank_str = f"{rank_num}위"
            
            # 변동 아이콘 추출
            change = "-"
            change_span = tds[1].select_one('span')
            if change_span:
                txt = change_span.get_text(strip=True).replace('n/a', '신규')
                if any(x in txt for x in ['▲', '▼', '신규']): change = txt

            # 제목 추출 (이미지나 점수에 밀리지 않도록 a 태그 우선)
            title_tag = tds[2].find('a')
            eng_title = title_tag.get_text(strip=True) if title_tag else tds[2].get_text(strip=True)
            kor_title = KOR_MAP.get(eng_title, eng_title)

            parsed.append({"rank": rank_str, "title": kor_title, "change": change})
        return parsed
    except: return []

def format_section(cfg):
    msg = f"🎬 **{cfg['name']}**\n"
    # 글로벌 리스트
    world = fetch_simple_ranking(cfg['id'], "world", cfg.get('lim', 10))
    if world:
        msg += " 🌎 글로벌 TOP\n"
        for i in world:
            msg += f" {i['rank']} **{i['title']}** | {i['change']}\n"
    # 한국 리스트
    if cfg.get('korea'):
        korea = fetch_simple_ranking(cfg['id'], "south-korea", 10)
        if korea:
            msg += "\n 🇰🇷 한국 TOP 10\n"
            for i in korea:
                msg += f" {i['rank']} **{i['title']}** | {i['change']}\n"
    return msg + "\n"

def send_msg(text):
    token, chat_id = os.environ.get("TELEGRAM_TOKEN"), os.environ.get("CHAT_ID")
    if token and chat_id:
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", 
                      json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})

def main():
    now = datetime.datetime.now().strftime("%y.%m.%d %H:%M")
    
    # 1번 메시지 (넷플릭스, 디즈니)
    m1 = f"🏆 **OTT 실시간 랭킹 [1/2] ({now})**\n━━━━━━━━━━━━━━━━━━\n\n"
    m1 += format_section({"id": "netflix", "name": "NETFLIX", "korea": True})
    m1 += format_section({"id": "disney", "name": "DISNEY+", "korea": True})
    send_msg(m1)
    
    time.sleep(2)
    
    # 2번 메시지 (나머지)
    m2 = f"🏆 **OTT 실시간 랭킹 [2/2] ({now})**\n━━━━━━━━━━━━━━━━━━\n\n"
    for p in [{"id": "apple-tv", "name": "APPLE TV+", "lim": 5}, 
              {"id": "amazon-prime", "name": "AMAZON PRIME", "lim": 5}, 
              {"id": "hbo", "name": "HBO MAX", "lim": 5}]:
        m2 += format_section(p)
    send_msg(m2)

if __name__ == "__main__":
    main()

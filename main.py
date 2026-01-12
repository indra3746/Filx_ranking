import requests
from bs4 import BeautifulSoup
import datetime
import os
import time

# 1. 한글 매핑 및 출시일 데이터베이스
CONTENT_DB = {
    "His & Hers": {"kor": "히스 앤 허스", "date": "26.01.08."},
    "People We Meet on Vacation": {"kor": "우리의 열 번째 여름", "date": "26.01.08."},
    "The Ugly": {"kor": "얼굴", "date": "26.01.09."},
    "Your Letter": {"kor": "연의 편지", "date": "26.01.12."},
    "The Great Flood": {"kor": "대홍수", "date": "26.01.09."},
    "Stranger Things": {"kor": "기묘한 이야기", "date": "16.07.15."},
    "Avatar: The Way of Water": {"kor": "아바타: 물의 길", "date": "22.12.16."},
    "TRON: Ares": {"kor": "트론: 아레스", "date": "25.12.25."}
}

def fetch_data(platform, loc="world", limit=10):
    url = f"https://flixpatrol.com/top10/{platform}/{loc}/today/"
    # 차단 방지를 위한 정밀 헤더 설정
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code != 200: return []
        
        soup = BeautifulSoup(res.text, 'html.parser')
        rows = soup.select('tr.table-group')
        data = []
        
        for row in rows[:limit]:
            tds = row.find_all('td')
            if len(tds) < 4: continue
            
            # 순위 및 변동
            rank = tds[0].get_text(strip=True).replace(".", "")
            change = "-"
            change_span = tds[1].select_one('span')
            if change_span:
                change = change_span.get_text(strip=True).replace('n/a', '신규')

            # 제목 추출 로직 강화 (텍스트가 비어있으면 속성값 참조)
            title_tag = tds[2].find('a') or tds[2]
            eng_title = title_tag.get_text(strip=True)
            if not eng_title: # 텍스트가 없을 경우 href 등에서 추출
                eng_title = title_tag.get('href', '').split('/')[-2].replace('-', ' ').title()

            # 점수 및 날짜
            idx = tds[3].get_text(strip=True)
            info = CONTENT_DB.get(eng_title, {"kor": eng_title, "date": "26.01.01."})
            
            data.append({
                "rank": rank, "change": change, "title": info['kor'], 
                "eng": eng_title, "idx": idx, "date": info['date']
            })
        return data
    except:
        return []

def format_section(cfg):
    msg = f"🎬 **{cfg['name']}**\n"
    
    # 글로벌 섹션
    world = fetch_data(cfg['id'], "world", cfg.get('lim', 10))
    if world:
        msg += f" 🌎 **글로벌 TOP {cfg.get('lim', 10)}**\n\n"
        for i in world:
            msg += f" {i['rank']}. {i['title']} | {i['idx']} ┃ {i['change']} ┃ {i['date']}\n"
    
    # 한국 섹션
    if cfg.get('korea'):
        korea = fetch_data(cfg['id'], "south-korea", 10)
        if korea:
            msg += f"\n 🇰🇷 **한국 TOP 10**\n\n"
            for i in korea:
                msg += f" {i['rank']}. {i['title']} ({i['eng']}) | {i['idx']} ┃ {i['change']} ┃ {i['date']}\n"
    return msg + "\n"

def send_telegram(text):
    # 환경 변수 이름을 CHAT_ID로 통일
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("CHAT_ID")
    if token and chat_id:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})

if __name__ == "__main__":
    now = datetime.datetime.now().strftime("%y.%m.%d %H:%M")
    
    # 메시지 분할 전송
    m1 = f"🏆 **OTT 통합 랭킹 [1/2] ({now})**\n━━━━━━━━━━━━━━━━━━\n\n"
    m1 += format_section({"id": "netflix", "name": "NETFLIX", "korea": True})
    m1 += format_section({"id": "disney", "name": "DISNEY+", "korea": True})
    send_telegram(m1)
    
    time.sleep(2) # 전송 안정성을 위한 지연
    
    m2 = f"🏆 **OTT 통합 랭킹 [2/2] ({now})**\n━━━━━━━━━━━━━━━━━━\n\n"
    for p in [{"id": "apple-tv", "name": "APPLE TV+", "lim": 5}, 
              {"id": "amazon-prime", "name": "AMAZON", "lim": 5}, 
              {"id": "hbo", "name": "HBO MAX", "lim": 5}]:
        m2 += format_section(p)
    send_telegram(m2)

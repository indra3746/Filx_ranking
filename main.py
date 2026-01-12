import requests
from bs4 import BeautifulSoup
import datetime
import os

# 한글 제목 매핑 (데이터가 확인된 주요 작품 우선)
KOR_TITLE_MAP = {
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
        res = requests.get(url, headers=headers, timeout=10)
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
            
            # 2. 제목 추출 (정확한 위치 타겟팅으로 숫자가 제목으로 나오는 버그 수정)
            title_tag = tds[2].find('a') or tds[2]
            eng_title = title_tag.get_text(strip=True)
            kor_title = KOR_TITLE_MAP.get(eng_title, eng_title)
            
            # 3. 점수(Index)와 기간(Days) 추출
            # 인덱스는 tds[3], 기간은 보통 tds[5] 또는 tds[-1] 부근에 위치
            idx = tds[3].get_text(strip=True)
            days = "1 d" # 기본값
            for td in tds:
                if ' d' in td.get_text():
                    days = td.get_text(strip=True)
                    break

            data.append({"rank": rank, "change": change, "title": kor_title, "eng": eng_title, "idx": idx, "days": days})
        return data
    except:
        return []

def format_section(cfg):
    msg = f"🎬 **{cfg['name']}**\n"
    
    # 글로벌 TOP (Days 표시)
    world = fetch_data(cfg['id'], "world", cfg.get('lim', 10))
    if world:
        msg += f" 🌎 **글로벌 TOP {len(world)}**\n\n"
        for i in world:
            msg += f" {i['rank']}. {i['title']} | {i['idx']} ┃ {i['change']} ┃ {i['days']}\n"
    
    # 한국 TOP (Days 표시)
    if cfg.get('korea'):
        korea = fetch_data(cfg['id'], "south-korea", 10)
        if korea:
            msg += f"\n 🇰🇷 **한국 TOP 10**\n\n"
            for i in korea:
                msg += f" {i['rank']}. {i['title']} ({i['eng']}) | {i['idx']} ┃ {i['change']} ┃ {i['days']}\n"
    return msg + "\n"

# (send_telegram 및 main 로직은 이전과 동일)

import requests
from bs4 import BeautifulSoup
import datetime
import os
import time

# 한글 제목 매핑 (URL 슬러그 기준)
KOR_MAP = {
    "the-pitt": "더 피트",
    "it-welcome-to-derry": "그것: 웰컴 투 데리",
    "the-family-plan-2": "패밀리 플랜 2",
    "his-hers": "히스 앤 허스",
    "the-ugly": "얼굴"
}

def fetch_data(platform_id, loc="world", limit=10):
    # HBO MAX의 실제 FlixPatrol 경로는 'hbo'입니다.
    actual_id = "hbo" if platform_id == "hbo-max" else platform_id
    url = f"https://flixpatrol.com/top10/{actual_id}/{loc}/today/"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=20)
        if res.status_code != 200: return []
        
        soup = BeautifulSoup(res.text, 'html.parser')
        rows = soup.select('tr.table-group')
        data = []
        
        for row in rows[:limit]:
            tds = row.find_all('td')
            if len(tds) < 3: continue
            
            # 1. 순위 (1열)
            rank = tds[0].get_text(strip=True).replace(".", "")
            
            # 2. 제목 추출 (숫자 오류 방지를 위해 a 태그의 title 또는 href 활용)
            title_link = row.find('a', href=True)
            if title_link:
                slug = title_link['href'].split('/')[-2]
                # title 속성이 있으면 사용, 없으면 슬러그를 제목으로 변환
                eng_title = title_link.get('title') or slug.replace('-', ' ').title()
                
                # 숫자로만 구성된 제목일 경우 슬러그에서 복원
                if eng_title.replace(".", "").isdigit():
                    eng_title = slug.replace('-', ' ').title()
                    
                kor_title = KOR_MAP.get(slug, eng_title)
            else:
                continue

            # 3. 변동 (2열)
            change = "-"
            change_span = tds[1].select_one('span')
            if change_span:
                txt = change_span.get_text(strip=True).replace('n/a', '신규')
                if any(x in txt for x in ['▲', '▼', '신규']): change = txt

            data.append({"rank": f"{rank}위", "title": kor_title, "change": change})
        return data
    except:
        return []

def format_section(cfg):
    msg = f"🎬 **{cfg['name']}**\n"
    items = fetch_data(cfg['id'], "world", cfg.get('lim', 10))
    if items:
        msg += " 🌎 글로벌 TOP\n"
        for i in items:
            msg += f" {i['rank']} **{i['title']}** | {i['change']}\n"
    
    if cfg.get('korea'):
        k_items = fetch_data(cfg['id'], "south-korea", 10)
        if k_items:
            msg += "\n 🇰🇷 한국 TOP 10\n"
            for i in k_items:
                msg += f" {i['rank']} **{i['title']}** | {i['change']}\n"
    return msg + "\n"

def send_telegram(text):
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("CHAT_ID")

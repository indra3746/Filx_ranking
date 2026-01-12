import requests
from bs4 import BeautifulSoup
import datetime
import os
import time

# 한글 매핑 DB (URL 슬러그 형태 대응)
KOR_MAP = {
    "his-hers": "히스 앤 허스",
    "people-we-meet-on-vacation": "우리의 열 번째 여름",
    "the-ugly": "얼굴",
    "your-letter": "연의 편지",
    "the-great-flood": "대홍수",
    "the-pitt": "더 피트",
    "it-welcome-to-derry": "그것: 웰컴 투 데리"
}

def fetch_safe_data(platform, loc="world", limit=10):
    # HBO Max는 현재 'hbo' 또는 'hbomax' 경로를 사용하므로 플랫폼 아이디 보정
    p_id = "hbo" if platform == "hbo-max" else platform
    url = f"https://flixpatrol.com/top10/{p_id}/{loc}/today/"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=20)
        if res.status_code != 200: return []
        
        soup = BeautifulSoup(res.text, 'html.parser')
        # 테이블 행(tr) 추출 시 헤더 제외
        rows = soup.select('tr.table-group')
        data = []
        
        for row in rows[:limit]:
            tds = row.find_all('td')
            if len(tds) < 3: continue
            
            # 1. 순위 (1열)
            rank = tds[0].get_text(strip=True).replace(".", "")
            
            # 2. 제목 추출 (가장 중요한 부분: title 속성 또는 URL 슬러그 활용)
            title_link = row.find('a', href=True)
            if title_link:
                # a 태그의 title 속성이 있으면 그것을 사용, 없으면 URL에서 추출
                raw_title = title_link.get('title') or title_link.get_text(strip=True)
                slug = title_link['href'].split('/')[-2]
                
                # 숫자로만 이루어진 제목일 경우 URL에서 복원
                if not raw_title or raw_title.replace(".", "").isdigit():
                    raw_title = slug.replace('-', ' ').title()
                
                kor_title = KOR_MAP.get(slug, raw_title)
            else:
                continue

            # 3. 변동 (2열 span)
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
    # 글로벌 리스트
    world = fetch_safe_data(cfg['id'], "world", cfg.get('lim', 10))
    if world:
        msg += " 🌎 글로벌 TOP\n"
        for i in world:
            msg += f" {i['rank']} **{i['title']}** | {i['change']}\n"
    # 한국 리스트
    if cfg.get('korea'):
        korea = fetch_safe_data(cfg['id'], "south-korea", 10)
        if korea:
            msg += "\n 🇰🇷 한국 TOP 10\n"
            for i in korea:
                msg += f" {i['rank']} **{i['title']}** | {i['change']}\n"
    return msg + "\n"

def send_telegram(text):
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("CHAT_ID")
    if token and chat_id:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})

def main():
    now = datetime.datetime.now().strftime("%y.%m.%d %H:%M")
    
    m1 = f"🏆 **OTT 실시간 랭킹 [1/2] ({now})**\n━━━━━━━━━━━━━━━━━━\n\n"
    m1 += format_section({"id": "netflix", "name": "NETFLIX", "korea": True})
    m1 += format_section({"id": "disney", "name": "DISNEY+", "korea": True})
    send_telegram(m1)
    
    time.sleep(2)
    
    m2 = f"🏆 **OTT 실시간 랭킹 [2/2] ({now})**\n━━━━━━━━━━━━━━━━━━\n\n"
    # HBO Max 아이디 수정 반영
    for p in [{"id": "apple-tv", "name": "APPLE TV+", "lim": 5}, 
              {"id": "amazon-prime", "name": "AMAZON PRIME", "lim": 5}, 
              {"id": "hbo", "name": "HBO MAX", "lim": 5}]:
        m2 += format_section(p)
    send_telegram(m2)

if __name__ == "__main__":
    main()

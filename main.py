import requests
from bs4 import BeautifulSoup
import datetime
import os
import time

# 한글 제목 매핑 (URL 슬러그 기준)
KOR_MAP = {
    "his-hers": "히스 앤 허스",
    "people-we-meet-on-vacation": "우리의 열 번째 여름",
    "the-ugly": "얼굴",
    "your-letter": "연의 편지",
    "the-great-flood": "대홍수",
    "the-pitt": "더 피트",
    "tron-ares": "트론: 아레스"
}

def fetch_data_robust(platform, loc="world", category="movies", limit=10):
    # 플랫폼 ID 보정 (HBO MAX는 내부적으로 hbo 사용)
    p_id = "hbo" if platform == "hbo-max" else platform
    
    # 카테고리별 정확한 경로 설정
    cat_path = "movies" if category == "movies" else ("tv-shows" if platform == "netflix" else "tv")
    url = f"https://flixpatrol.com/top10/{p_id}/{loc}/today/{cat_path}/"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=20)
        if res.status_code != 200: return []
        
        soup = BeautifulSoup(res.text, 'html.parser')
        # 테이블 행 추출 로직 강화
        rows = soup.find_all('tr', class_='table-group')
        if not rows: # 클래스명이 없을 경우 모든 tr 조사
            rows = soup.select('table tr')[1:] 
            
        data = []
        for row in rows[:limit]:
            tds = row.find_all('td')
            if len(tds) < 3: continue
            
            # 1. 순위 추출
            rank_text = tds[0].get_text(strip=True).replace(".", "")
            rank = f"{rank_text}위" if rank_text.isdigit() else rank_text

            # 2. 제목 추출 (링크 title 또는 URL 슬러그에서 강제 추출)
            title_link = row.find('a', href=True)
            if title_link:
                slug = title_link['href'].split('/')[-2]
                raw_title = title_link.get('title') or title_link.get_text(strip=True)
                # 숫자로 깨질 경우 URL 슬러그에서 이름 복원
                if not raw_title or raw_title.replace(".", "").isdigit():
                    raw_title = slug.replace('-', ' ').title()
                title = KOR_MAP.get(slug, raw_title)
            else: continue

            # 3. 순위 변동
            change = "-"
            change_span = tds[1].select_one('span')
            if change_span:
                txt = change_span.get_text(strip=True).replace('n/a', '신규')
                if any(x in txt for x in ['▲', '▼', '신규']): change = txt

            data.append({"rank": rank, "title": title, "change": change})
            
        return data
    except Exception as e:
        print(f"Error fetching {platform}: {e}")
        return []

def format_full_msg(p_cfg):
    msg = f"🎬 **{p_cfg['name']}**\n"
    # 글로벌: 영화와 TV 쇼를 각각 호출하여 구분
    for cat in ["movies", "tv"]:
        label = "영화" if cat == "movies" else "TV 쇼"
        items = fetch_data_robust(p_cfg['id'], "world", cat, 10)
        if items:
            msg += f" 🌎 글로벌 TOP 10 ({label})\n"
            for i in items:
                msg += f" {i['rank']} **{i['title']}** | {i['change']}\n"
            msg += "\n"
    
    # 한국: 통합 랭킹 (요청 시 카테고리 분리 가능)
    if p_cfg.get('korea'):
        k_items = fetch_data_robust(p_cfg['id'], "south-korea", "movies", 10) # 예시로 영화 우선
        if k_items:
            msg += " 🇰🇷 한국 TOP 10\n"
            for i in k_items:
                msg += f" {i['rank']} **{i['title']}** | {i['change']}\n"
    return msg + "\n"

def send_msg(text):
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("CHAT_ID")
    if token and chat_id:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})

def main():
    # 한국 시간(KST) 기준 설정
    kst_now = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
    time_str = kst_now.strftime("%y.%m.%d %H:%M")
    
    # 1. NETFLIX
    m1 = f"🏆 **[1/3] NETFLIX 실시간 랭킹 ({time_str})**\n━━━━━━━━━━━━━━━━━━\n\n"
    m1 += format_full_msg({"id": "netflix", "name": "NETFLIX", "korea": True})
    send_msg(m1)
    time.sleep(2)
    
    # 2. DISNEY+
    m2 = f"🏆 **[2/3] DISNEY+ 실시간 랭킹 ({time_str})**\n━━━━━━━━━━━━━━━━━━\n\n"
    m2 += format_full_msg({"id": "disney", "name": "DISNEY+", "korea": True})
    send_msg(m2)
    time.sleep(2)
    
    # 3. 기타 (APPLE, AMAZON, HBO)
    m3 = f"🏆 **[3/3] 기타 OTT 통합 랭킹 ({time_str})**\n━━━━━━━━━━━━━━━━━━\n\n"
    for p in [{"id": "apple-tv", "name": "APPLE TV+"}, 
              {"id": "amazon-prime", "name": "AMAZON PRIME"}, 
              {"id": "hbo-max", "name": "HBO MAX"}]:
        m3 += format_full_msg(p)
    send_msg(m3)

if __name__ == "__main__":
    main()

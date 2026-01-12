import requests
from bs4 import BeautifulSoup
import datetime
import os
import time

# 한글 제목 매핑 DB
KOR_MAP = {
    "his-hers": "히스 앤 허스",
    "the-pitt": "더 피트",
    "tron-ares": "트론: 아레스",
    "the-ugly": "얼굴",
    "your-letter": "연의 편지"
}

def fetch_data(platform, loc="world", category="movies", limit=10):
    # 플랫폼별 실제 경로 보정
    p_id = "hbo" if platform == "hbo-max" else platform
    
    # 카테고리별 정확한 경로 설정
    # 넷플릭스는 'tv-shows', 나머지는 'tv' 사용
    cat_path = "movies" if category == "movies" else ("tv-shows" if platform == "netflix" else "tv")
    
    url = f"https://flixpatrol.com/top10/{p_id}/{loc}/today/{cat_path}/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        res = requests.get(url, headers=headers, timeout=20)
        soup = BeautifulSoup(res.text, 'html.parser')
        rows = soup.select('tr.table-group')
        data = []
        
        for row in rows[:limit]:
            tds = row.find_all('td')
            if len(tds) < 3: continue
            
            rank = tds[0].get_text(strip=True).replace(".", "")
            
            # 제목 추출 (숫자 오류 방지 로직)
            title_link = row.find('a', href=True)
            if title_link:
                slug = title_link['href'].split('/')[-2]
                raw_title = title_link.get('title') or slug.replace('-', ' ').title()
                if raw_title.replace(".", "").isdigit():
                    raw_title = slug.replace('-', ' ').title()
                title = KOR_MAP.get(slug, raw_title)
            else: continue

            change = "-"
            change_span = tds[1].select_one('span')
            if change_span:
                txt = change_span.get_text(strip=True).replace('n/a', '신규')
                if any(x in txt for x in ['▲', '▼', '신규']): change = txt

            data.append({"rank": f"{rank}위", "title": title, "change": change})
        return data
    except: return []

def format_full_report(cfg):
    msg = f"🎬 **{cfg['name']}**\n"
    # 글로벌 & 한국 각각 영화/TV쇼 분리 추출
    targets = [("world", "🌎 글로벌"), ("south-korea", "🇰🇷 한국")] if cfg.get('korea') else [("world", "🌎 글로벌")]
    
    for loc_id, loc_label in targets:
        for cat in ["movies", "tv"]:
            label = "영화" if cat == "movies" else "TV 쇼"
            items = fetch_data(cfg['id'], loc_id, cat, 10 if loc_id == "world" else 10)
            if items:
                msg += f" {loc_label} TOP 10 ({label})\n"
                for i in items:
                    msg += f" {i['rank']} **{i['title']}** | {i['change']}\n"
                msg += "\n"
    return msg

def send_msg(text):
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("CHAT_ID")
    if token and chat_id:
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", 
                      json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})

def main():
    # 한국 시간(KST) 기준
    kst_now = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
    time_str = kst_now.strftime("%y.%m.%d %H:%M")
    
    # 1. 넷플릭스
    send_msg(f"🏆 **[1/3] NETFLIX 실시간 랭킹 ({time_str})**\n━━━━━━━━━━━━━━━━━━\n\n" + 
             format_full_report({"id": "netflix", "name": "NETFLIX", "korea": True}))
    time.sleep(2)
    
    # 2. 디즈니+
    send_msg(f"🏆 **[2/3] DISNEY+ 실시간 랭킹 ({time_str})**\n━━━━━━━━━━━━━━━━━━\n\n" + 
             format_full_report({"id": "disney", "name": "DISNEY+", "korea": True}))
    time.sleep(2)
    
    # 3. 기타 플랫폼
    m3 = f"🏆 **[3/3] 기타 OTT 통합 랭킹 ({time_str})**\n━━━━━━━━━━━━━━━━━━\n\n"
    for p in [{"id": "apple-tv", "name": "APPLE TV+"}, 
              {"id": "amazon-prime", "name": "AMAZON PRIME"}, 
              {"id": "hbo-max", "name": "HBO MAX"}]:
        m3 += format_full_report(p)
    send_msg(m3)

if __name__ == "__main__":
    main()

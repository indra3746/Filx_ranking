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
    "your-letter": "연의 편지",
    "the-great-flood": "대홍수"
}

def fetch_safe_ranking(platform, loc="world", category="full", limit=10):
    # 플랫폼별 실제 경로 보정
    p_id = "hbo" if platform == "hbo-max" else platform
    
    # 카테고리별 URL 구성 최적화
    cat_path = ""
    if category == "movies": cat_path = "movies/"
    elif category == "tv": cat_path = "tv-shows/" if platform == "netflix" else "tv/" # 플랫폼별 상이
    
    url = f"https://flixpatrol.com/top10/{p_id}/{loc}/today/{cat_path}"
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
            
            # 제목 추출 (링크 title 또는 URL 슬러그 활용)
            title_link = row.find('a', href=True)
            if title_link:
                slug = title_link['href'].split('/')[-2]
                raw_title = title_link.get('title') or slug.replace('-', ' ').title()
                # 숫자로 깨질 경우 슬러그에서 복원
                if raw_title.replace(".", "").isdigit():
                    raw_title = slug.replace('-', ' ').title()
                title = KOR_MAP.get(slug, raw_title)
            else: continue

            # 변동 정보
            change = "-"
            change_span = tds[1].select_one('span')
            if change_span:
                txt = change_span.get_text(strip=True).replace('n/a', '신규')
                if any(x in txt for x in ['▲', '▼', '신규']): change = txt

            data.append({"rank": f"{rank}위", "title": title, "change": change})
        return data
    except: return []

def format_platform_msg(p_cfg):
    msg = f"🎬 **{p_cfg['name']}**\n"
    # 글로벌: 영화 / TV 쇼 분리
    for cat, label in [("movies", "영화"), ("tv", "TV 쇼")]:
        items = fetch_safe_ranking(p_cfg['id'], "world", cat, 10 if p_cfg.get('korea') else 5)
        if items:
            msg += f" 🌎 글로벌 TOP ({label})\n"
            for i in items:
                msg += f" {i['rank']} **{i['title']}** | {i['change']}\n"
            msg += "\n"
    
    # 한국: 통합 랭킹
    if p_cfg.get('korea'):
        k_items = fetch_safe_ranking(p_cfg['id'], "south-korea", "full", 10)
        if k_items:
            msg += " 🇰🇷 한국 TOP 10\n"
            for i in k_items:
                msg += f" {i['rank']} **{i['title']}** | {i['change']}\n"
    return msg

def send_to_telegram(text):
    token, chat_id = os.environ.get("TELEGRAM_TOKEN"), os.environ.get("CHAT_ID")
    if token and chat_id:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})

def main():
    # 한국 시간(KST) 기준 시간 문자열 생성
    kst = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
    time_tag = kst.strftime("%y.%m.%d %H:%M")
    
    # 1. NETFLIX
    m1 = f"🏆 **[1/3] NETFLIX 실시간 랭킹 ({time_tag})**\n━━━━━━━━━━━━━━━━━━\n\n"
    m1 += format_platform_msg({"id": "netflix", "name": "NETFLIX", "korea": True})
    send_to_telegram(m1)
    time.sleep(2)
    
    # 2. DISNEY+
    m2 = f"🏆 **[2/3] DISNEY+ 실시간 랭킹 ({time_tag})**\n━━━━━━━━━━━━━━━━━━\n\n"
    m2 += format_platform_msg({"id": "disney", "name": "DISNEY+", "korea": True})
    send_to_telegram(m2)
    time.sleep(2)
    
    # 3. 기타 플랫폼 (HBO MAX 데이터 복구 포함)
    m3 = f"🏆 **[3/3] 기타 OTT 통합 랭킹 ({time_tag})**\n━━━━━━━━━━━━━━━━━━\n\n"
    for p in [{"id": "apple-tv", "name": "APPLE TV+"}, 
              {"id": "amazon-prime", "name": "AMAZON PRIME"}, 
              {"id": "hbo-max", "name": "HBO MAX"}]:
        m3 += format_platform_msg(p)
    send_to_telegram(m3)

if __name__ == "__main__":
    main()

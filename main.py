import requests
from bs4 import BeautifulSoup
import datetime
import os
import time

# 한글 제목 매핑 DB
KOR_MAP = {
    "his-hers": "히스 앤 허스",
    "people-we-meet-on-vacation": "우리의 열 번째 여름",
    "the-ugly": "얼굴",
    "your-letter": "연의 편지",
    "the-great-flood": "대홍수",
    "tron-ares": "트론: 아레스"
}

def fetch_safe_ranking(platform, loc="world", category="movies", limit=10):
    # HBO MAX 경로 보정
    p_id = "hbo" if platform == "hbo-max" else platform
    
    # 카테고리별 경로 설정
    if platform == "netflix":
        cat_path = "movies" if category == "movies" else "tv-shows"
    else:
        cat_path = "movies" if category == "movies" else "tv"
    
    url = f"https://flixpatrol.com/top10/{p_id}/{loc}/today/{cat_path}/"
    
    # [핵심] 차단 회피를 위한 정밀 브라우저 헤더 설정
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache',
        'Referer': 'https://flixpatrol.com/'
    }
    
    try:
        # 응답 지연에 대비한 timeout 설정
        res = requests.get(url, headers=headers, timeout=30)
        if res.status_code != 200:
            print(f"차단됨: {platform} {loc} (코드: {res.status_code})")
            return []
        
        soup = BeautifulSoup(res.text, 'html.parser')
        # 테이블 구조 정밀 타겟팅
        rows = soup.select('tr.table-group')
        if not rows:
            # 대체 구조 탐색 (구조 변경 대비)
            rows = soup.find_all('tr', class_=lambda x: x and 'table-group' in x)
            
        data = []
        for row in rows[:limit]:
            tds = row.find_all('td')
            if len(tds) < 3: continue
            
            rank = tds[0].get_text(strip=True).replace(".", "")
            
            # 제목 추출 (이미지 속성 또는 링크 활용)
            title_link = row.find('a', href=True)
            if title_link:
                slug = title_link['href'].split('/')[-2]
                raw_title = title_link.get('title') or title_link.get_text(strip=True)
                # 숫자로 깨질 경우 슬러그에서 이름 복원
                if not raw_title or raw_title.replace(".", "").isdigit():
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
    except Exception as e:
        print(f"에러 발생 ({platform}): {e}")
        return []

def format_full_report(p_cfg):
    msg = f"🎬 **{p_cfg['name']}**\n"
    # 영화/TV 쇼 각각 데이터 수집
    for cat in ["movies", "tv"]:
        label = "영화" if cat == "movies" else "TV 쇼"
        items = fetch_safe_ranking(p_cfg['id'], "world", cat, 10)
        if items:
            msg += f" 🌎 글로벌 TOP 10 ({label})\n"
            for i in items:
                msg += f" {i['rank']} **{i['title']}** | {i['change']}\n"
            msg += "\n"
        else:
            print(f"데이터 수집 실패: {p_cfg['name']} 글로벌 {label}")
    
    # 한국 랭킹
    if p_cfg.get('korea'):
        k_items = fetch_safe_ranking(p_cfg['id'], "south-korea", "movies", 10)
        if k_items:
            msg += " 🇰🇷 한국 TOP 10\n"
            for i in k_items:
                msg += f" {i['rank']} **{i['title']}** | {i['change']}\n"
        else:
            print(f"데이터 수집 실패: {p_cfg['name']} 한국 랭킹")
    return msg

def send_msg(text):
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("CHAT_ID")
    if token and chat_id:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        # 메시지 길이가 0일 경우 전송 생략
        if len(text.strip()) > 50:
            requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})

def main():
    # 최신 datetime.now(datetime.UTC) 사용 권장 (DeprecationWarning 해결)
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    kst_now = now_utc + datetime.timedelta(hours=9)
    time_str = kst_now.strftime("%y.%m.%d %H:%M")
    
    # 1. NETFLIX
    m1 = f"🏆 **[1/3] NETFLIX 실시간 랭킹 ({time_str})**\n━━━━━━━━━━━━━━━━━━\n\n"
    m1 += format_full_report({"id": "netflix", "name": "NETFLIX", "korea": True})
    send_msg(m1)
    time.sleep(3) # 전송 지연 간격 확대
    
    # 2. DISNEY+
    m2 = f"🏆 **[2/3] DISNEY+ 실시간 랭킹 ({time_str})**\n━━━━━━━━━━━━━━━━━━\n\n"
    m2 += format_full_report({"id": "disney", "name": "DISNEY+", "korea": True})
    send_msg(m2)
    time.sleep(3)
    
    # 3. 기타 플랫폼 (HBO MAX 포함)
    m3 = f"🏆 **[3/3] 기타 OTT 통합 랭킹 ({time_str})**\n━━━━━━━━━━━━━━━━━━\n\n"
    for p in [{"id": "apple-tv", "name": "APPLE TV+"}, 
              {"id": "amazon-prime", "name": "AMAZON PRIME"}, 
              {"id": "hbo-max", "name": "HBO MAX"}]:
        m3 += format_full_report(p)
    send_msg(m3)

if __name__ == "__main__":
    main()

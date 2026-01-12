import requests
from bs4 import BeautifulSoup
import datetime
import os
import time
import sys

# 1. 한글 제목 매핑 DB
KOR_MAP = {
    "his-hers": "히스 앤 허스",
    "people-we-meet-on-vacation": "우리의 열 번째 여름",
    "the-ugly": "얼굴",
    "your-letter": "연의 편지",
    "the-great-flood": "대홍수",
    "tron-ares": "트론: 아레스",
    "made-in-korea": "메이드 인 코리아",
    "culinary-class-wars": "흑백요리사",
    "squid-game": "오징어 게임",
    "the-pitt": "더 피트",
    "stranger-things": "기묘한 이야기",
    "emily-in-paris": "에밀리, 파리에 가다"
}

# 2. 텔레그램 전송 함수
def send_telegram(text):
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("CHAT_ID")
    if token and chat_id and len(text) > 10:
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})
        except Exception as e:
            print(f"전송 실패: {e}")

# 3. 데이터 수집 함수 (베이스 URL 방식)
def fetch_rankings(platform, loc="world"):
    # 플랫폼 ID 보정
    p_id = "hbo" if platform == "hbo-max" else platform
    
    # [핵심] 날짜나 categories 없이 베이스 주소로 접속 -> 사이트가 알아서 최신 페이지로 연결해줌
    url = f"https://flixpatrol.com/top10/{p_id}/{loc}/"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
    }
    
    print(f"[{platform}] 접속 시도: {url}")
    
    try:
        res = requests.get(url, headers=headers, timeout=30)
        if res.status_code != 200:
            print(f"❌ 접속 실패 ({res.status_code})")
            return {"movies": [], "tv": []}
            
        soup = BeautifulSoup(res.text, 'html.parser')
        
        movies = []
        tv = []
        
        # 페이지 내의 모든 테이블 그룹을 찾음
        # 보통 첫번째가 영화, 두번째가 TV쇼임 (헤더 텍스트로 확인)
        blocks = soup.find_all('div', class_='content-block')
        
        # 블록 단위로 파싱 시도
        if blocks:
            for block in blocks:
                header_tag = block.find_previous('h2')
                header_text = header_tag.get_text(strip=True).lower() if header_tag else ""
                
                # 테이블 찾기
                tbody = block.find('tbody', class_='table-group')
                if not tbody: continue
                
                items = parse_tbody(tbody)
                
                if 'movie' in header_text or 'film' in header_text:
                    movies = items
                elif 'tv' in header_text or 'show' in header_text:
                    tv = items
                # 헤더가 없거나 모호하면 순서대로 채움
                elif not movies:
                    movies = items
                else:
                    tv = items
        else:
            # 블록 구조가 아니면 단순 테이블 순서로 파싱 (Fallback)
            tbodies = soup.select('tbody.table-group')
            for i, tbody in enumerate(tbodies):
                items = parse_tbody(tbody)
                if i == 0: movies = items
                elif i == 1: tv = items

        return {"movies": movies, "tv": tv}

    except Exception as e:
        print(f"⚠️ 에러 발생 ({platform}): {e}")
        return {"movies": [], "tv": []}

# 4. 테이블 파싱 헬퍼 함수
def parse_tbody(tbody):
    results = []
    rows = tbody.find_all('tr')
    for row in rows[:10]: # TOP 10만
        tds = row.find_all('td')
        if len(tds) < 2: continue
        
        rank = tds[0].get_text(strip=True).replace(".", "")
        
        # 제목 추출
        title_link = row.find('a', href=True)
        title = "-"
        if title_link:
            slug = title_link['href'].split('/')[-2]
            # 텍스트가 없거나 숫자면 title 속성이나 슬러그 사용
            raw = title_link.get_text(strip=True)
            if not raw or raw.replace(".", "").isdigit():
                raw = title_link.get('title') or slug.replace('-', ' ').title()
            
            title = KOR_MAP.get(slug, raw)
            
        # 변동
        change = "-"
        if len(tds) > 1:
            span = tds[1].select_one('span')
            if span: change = span.get_text(strip=True).replace('n/a', '신규')
            
        results.append(f"{rank}위 {title} | {change}")
    return results

# 5. 메시지 포맷팅 함수
def format_msg(name, data):
    msg = f"🎬 **{name}**\n"
    has_data = False
    
    if data['movies']:
        msg += " 🌎 글로벌 TOP 10 (영화)\n" + "\n".join([f" {x}" for x in data['movies']]) + "\n\n"
        has_data = True
    if data['tv']:
        msg += " 🌎 글로벌 TOP 10 (TV 쇼)\n" + "\n".join([f" {x}" for x in data['tv']]) + "\n\n"
        has_data = True
        
    if not has_data:
        msg += " (데이터 수집 실패 또는 집계 중)\n\n"
        
    return msg

# 6. 메인 실행 함수
def main():
    # DeprecationWarning 해결을 위한 timezone 설정
    now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9)
    time_str = now.strftime("%y.%m.%d %H:%M")
    
    print(f"--- 실행 시작 ({time_str}) ---")
    
    # [1] NETFLIX
    n_world = fetch_rankings("netflix", "world")
    n_kr = fetch_rankings("netflix", "south-korea")
    
    m1 = f"🏆 **[1/3] NETFLIX 실시간 랭킹 ({time_str})**\n━━━━━━━━━━━━━━━━━━\n\n"
    m1 += format_msg("NETFLIX Global", n_world)
    
    # 넷플릭스 한국 데이터 추가
    if n_kr['movies'] or n_kr['tv']:
        m1 += " 🇰🇷 **한국 TOP 10**\n"
        if n_kr['movies']: m1 += " [영화]\n" + "\n".join([f" {x}" for x in n_kr['movies'][:5]]) + "\n"
        if n_kr['tv']: m1 += " [TV 쇼]\n" + "\n".join([f" {x}" for x in n_kr['tv'][:5]]) + "\n"
    
    send_telegram(m1)
    time.sleep(3)
    
    # [2] DISNEY+
    d_world = fetch_rankings("disney", "world")
    m2 = f"🏆 **[2/3] DISNEY+ 실시간 랭킹 ({time_str})**\n━━━━━━━━━━━━━━━━━━\n\n"
    m2 += format_msg("DISNEY+", d_world)
    send_telegram(m2)
    time.sleep(3)
    
    # [3] 기타 플랫폼
    m3 = f"🏆 **[3/3] 기타 OTT 통합 랭킹 ({time_str})**\n━━━━━━━━━━━━━━━━━━\n\n"
    
    hbo = fetch_rankings("hbo-max", "world")
    if hbo['movies'] or hbo['tv']: m3 += format_msg("HBO MAX", hbo)
    
    amz = fetch_rankings("amazon-prime", "world")
    if amz['movies'] or amz['tv']: m3 += format_msg("AMAZON PRIME", amz)
    
    send_telegram(m3)
    print("--- 실행 완료 ---")

if __name__ == "__main__":
    main()

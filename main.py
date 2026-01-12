import requests
from bs4 import BeautifulSoup
import datetime
import os
import time

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

# 2. 텔레그램 전송
def send_telegram(text):
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("CHAT_ID")
    if token and chat_id and len(text) > 10:
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})
        except Exception as e:
            print(f"전송 실패: {e}")

# 3. 데이터 수집 함수 (HBO 404 대응 추가)
def fetch_rankings(platform, loc="world"):
    # 플랫폼 ID 처리 (hbo-max는 'hbo'로, 실패 시 'hbo-max'로 재시도 가능하게 설계)
    p_ids = ["hbo"] if platform == "hbo-max" else [platform]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
    }

    # HBO의 경우 404가 뜨면 대체 ID로 시도할 수 있도록 반복문 구성
    for pid in p_ids:
        url = f"https://flixpatrol.com/top10/{pid}/{loc}/"
        print(f"[{platform}] 접속 시도: {url}")
        
        try:
            res = requests.get(url, headers=headers, timeout=30)
            if res.status_code == 404:
                print(f"⚠️ {pid} 경로 404 발생. (데이터 없음)")
                continue # 다음 ID 시도 혹은 빈 값 반환
            
            if res.status_code != 200:
                print(f"❌ 접속 실패 ({res.status_code})")
                continue

            soup = BeautifulSoup(res.text, 'html.parser')
            movies, tv = [], []
            
            # 컨텐츠 블록 파싱
            blocks = soup.find_all('div', class_='content-block')
            if blocks:
                for block in blocks:
                    header = block.find_previous('h2')
                    h_text = header.get_text(strip=True).lower() if header else ""
                    tbody = block.find('tbody', class_='table-group')
                    if not tbody: continue
                    
                    items = parse_tbody(tbody)
                    if 'movie' in h_text or 'film' in h_text: movies = items
                    elif 'tv' in h_text or 'show' in h_text: tv = items
                    elif not movies: movies = items
                    else: tv = items
            else:
                # 블록 구조가 아닐 경우 단순 테이블 순서
                tbodies = soup.select('tbody.table-group')
                for i, tbody in enumerate(tbodies):
                    items = parse_tbody(tbody)
                    if i == 0: movies = items
                    elif i == 1: tv = items
            
            return {"movies": movies, "tv": tv}

        except Exception as e:
            print(f"⚠️ 에러 발생 ({pid}): {e}")
            
    return {"movies": [], "tv": []}

# 4. 테이블 파싱
def parse_tbody(tbody):
    results = []
    rows = tbody.find_all('tr')
    for row in rows[:10]:
        tds = row.find_all('td')
        if len(tds) < 2: continue
        
        rank = tds[0].get_text(strip=True).replace(".", "")
        title_link = row.find('a', href=True)
        title = "-"
        if title_link:
            slug = title_link['href'].split('/')[-2]
            raw = title_link.get_text(strip=True)
            if not raw or raw.replace(".", "").isdigit():
                raw = title_link.get('title') or slug.replace('-', ' ').title()
            title = KOR_MAP.get(slug, raw)
            
        change = "-"
        if len(tds) > 1:
            span = tds[1].select_one('span')
            if span: change = span.get_text(strip=True).replace('n/a', '신규')
            
        results.append(f"{rank}위 {title} | {change}")
    return results

# 5. 메시지 포맷팅
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
        msg += " (데이터 집계 중 또는 랭킹 없음)\n\n"
        
    return msg

# 6. 메인 실행
def main():
    now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9)
    time_str = now.strftime("%y.%m.%d %H:%M")
    
    print(f"--- 실행 시작 ({time_str}) ---")
    
    # 1. NETFLIX
    n_world = fetch_rankings("netflix", "world")
    n_kr = fetch_rankings("netflix", "south-korea")
    
    m1 = f"🏆 **[1/3] NETFLIX 실시간 랭킹 ({time_str})**\n━━━━━━━━━━━━━━━━━━\n\n"
    m1 += format_msg("NETFLIX Global", n_world)
    if n_kr['movies'] or n_kr['tv']:
        m1 += " 🇰🇷 **한국 TOP 10**\n"
        if n_kr['movies']: m1 += " [영화]\n" + "\n".join([f" {x}" for x in n_kr['movies'][:5]]) + "\n"
        if n_kr['tv']: m1 += " [TV 쇼]\n" + "\n".join([f" {x}" for x in n_kr['tv'][:5]]) + "\n"
    send_telegram(m1)
    time.sleep(3)
    
    # 2. DISNEY+
    d_world = fetch_rankings("disney", "world")
    m2 = f"🏆 **[2/3] DISNEY+ 실시간 랭킹 ({time_str})**\n━━━━━━━━━━━━━━━━━━\n\n"
    m2 += format_msg("DISNEY+", d_world)
    send_telegram(m2)
    time.sleep(3)
    
    # 3. 기타 (HBO 404 예외 처리 적용됨)
    m3 = f"🏆 **[3/3] 기타 OTT 통합 랭킹 ({time_str})**\n━━━━━━━━━━━━━━━━━━\n\n"
    hbo = fetch_rankings("hbo-max", "world")
    if hbo['movies'] or hbo['tv']: m3 += format_msg("HBO MAX", hbo)
    
    amz = fetch_rankings("amazon-prime", "world")
    if amz['movies'] or amz['tv']: m3 += format_msg("AMAZON PRIME", amz)
    
    send_telegram(m3)
    print("--- 완료 ---")

if __name__ == "__main__":
    main()

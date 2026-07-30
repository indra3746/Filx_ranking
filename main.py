import os
import time
import datetime
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

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
            requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown", "disable_web_page_preview": True})
        except Exception as e:
            print(f"전송 실패: {e}")

# 3. 데이터 수집 함수 (FlixPatrol 최신 구조 대응 및 강화된 우회)
def fetch_rankings(browser, platform, loc="world"):
    if platform == "hbo-max":
        p_ids = ["hbo", "max", "hbo-max"]
    else:
        p_ids = [platform]
        
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        viewport={'width': 1920, 'height': 1080},
        locale="en-US"
    )
    
    # 봇 감지 메커니즘 무력화
    context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        window.chrome = { runtime: {} };
    """)
    page = context.new_page()

    for pid in p_ids:
        url = f"https://flixpatrol.com/top10/{pid}/{loc}/"
        print(f"[{platform}] Playwright 접속 시도: {url}")
        
        try:
            page.goto(url, wait_until="networkidle", timeout=45000)
            page.wait_for_timeout(4000)
            
            html_content = page.content()
            soup = BeautifulSoup(html_content, 'html.parser')
            
            movies = []
            tv = []
            
            # [전략 1] 카드형/그리드형 또는 테이블 구조 탐색
            # 링크(a 태그) 중 /title/ 경로를 포함하는 순위 데이터 파싱
            rank_items = soup.find_all(['tr', 'div', 'li'])
            
            temp_movies = []
            temp_tv = []
            current_category = None
            
            # 카테고리 헤더 탐색
            sections = soup.find_all(['div', 'section', 'article'])
            for sec in sections:
                sec_text = sec.get_text(strip=True).lower()
                
                # 영화/TV 영역 구분
                links = sec.find_all('a')
                valid_links = []
                for a in links:
                    href = a.get('href', '')
                    if '/title/' in href or '/top10/' in href:
                        txt = a.get_text(strip=True)
                        if txt and txt not in valid_links and len(txt) > 1:
                            valid_links.append(txt)
                
                if valid_links:
                    if 'movie' in sec_text and not temp_movies:
                        temp_movies = valid_links[:10]
                    elif ('tv' in sec_text or 'show' in sec_text) and not temp_tv:
                        temp_tv = valid_links[:10]

            # [전략 2] 기존 테이블 구조 백업 파싱
            if not temp_movies and not temp_tv:
                for header in soup.find_all(['h1', 'h2', 'h3', 'h4', 'div']):
                    h_text = header.get_text(strip=True).lower()
                    if 'movie' in h_text or 'tv' in h_text:
                        parent = header.parent
                        row_links = parent.find_all('a') if parent else []
                        parsed = []
                        for l in row_links:
                            t = l.get_text(strip=True)
                            if t and t not in parsed and len(t) > 1:
                                slug = l.get('href', '').split('/')[-2] if '/' in l.get('href', '') else ""
                                title = KOR_MAP.get(slug, t)
                                parsed.append(title)
                                if len(parsed) == 10: break
                        
                        if 'movie' in h_text and not temp_movies:
                            temp_movies = parsed
                        elif 'tv' in h_text and not temp_tv:
                            temp_tv = parsed

            # 번호 매기기 포맷 적용
            if temp_movies:
                movies = [f"{idx+1}위 {title}" for idx, title in enumerate(temp_movies)]
            if temp_tv:
                tv = [f"{idx+1}위 {title}" for idx, title in enumerate(temp_tv)]

            if movies or tv:
                context.close()
                return {"movies": movies, "tv": tv}

        except Exception as e:
            print(f"⚠️ 에러 ({pid}): {e}")
            
    context.close()
    return {"movies": [], "tv": []}

# 4. 메시지 포맷팅
def format_msg(name, data, limit=10):
    msg = f"🎬 **{name}**\n"
    has_data = False
    
    if data['movies']:
        msg += f" 🌎 글로벌 TOP {limit} (영화)\n"
        msg += "\n".join([f" {x}" for x in data['movies'][:limit]]) + "\n\n"
        has_data = True
        
    if data['tv']:
        msg += f" 🌎 글로벌 TOP {limit} (TV 쇼)\n"
        msg += "\n".join([f" {x}" for x in data['tv'][:limit]]) + "\n\n"
        has_data = True
        
    if not has_data:
        msg += " (데이터 없음)\n\n"
    return msg

# 5. 한국 랭킹 포맷팅 함수
def format_korea_ranking(data):
    msg = ""
    if data['movies'] or data['tv']:
        msg += " 🇰🇷 **한국 TOP 10**\n"
        
        if data['movies']:
            msg += " 🎞️ **영화**\n"
            msg += "\n".join([f" {x}" for x in data['movies'][:10]]) + "\n\n" 
            
        if data['tv']:
            msg += " 📺 **TV 쇼**\n"
            msg += "\n".join([f" {x}" for x in data['tv'][:10]]) + "\n\n" 
    return msg

# 6. 메인 로직
def main():
    now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9)
    time_str = now.strftime("%y.%m.%d %H:%M")
    
    print(f"--- 실행 ({time_str}) ---")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-infobars'
            ]
        )
        
        # [1] NETFLIX
        n_world = fetch_rankings(browser, "netflix", "world")
        n_kr = fetch_rankings(browser, "netflix", "south-korea")
        
        m1 = f"🏆 **[1/3] NETFLIX 실시간 랭킹 ({time_str})**\n━━━━━━━━━━━━━━━━━━\n\n"
        m1 += format_msg("NETFLIX Global", n_world, limit=10)
        m1 += format_korea_ranking(n_kr)
        m1 += "🔗 [상세보기](https://flixpatrol.com/top10/netflix/)\n"
        
        send_telegram(m1)
        time.sleep(3)
        
        # [2] DISNEY+
        d_world = fetch_rankings(browser, "disney", "world")
        d_kr = fetch_rankings(browser, "disney", "south-korea") 
        
        m2 = f"🏆 **[2/3] DISNEY+ 실시간 랭킹 ({time_str})**\n━━━━━━━━━━━━━━━━━━\n\n"
        m2 += format_msg("DISNEY+", d_world, limit=10)
        m2 += format_korea_ranking(d_kr) 
        m2 += "🔗 [상세보기](https://flixpatrol.com/top10/disney/)\n" 
        
        send_telegram(m2)
        time.sleep(3)
        
        # [3] 기타 (HBO MAX, AMAZON, APPLE)
        m3 = f"🏆 **[3/3] 기타 OTT 통합 랭킹 ({time_str})**\n━━━━━━━━━━━━━━━━━━\n\n"
        
        hbo = fetch_rankings(browser, "hbo-max", "world")
        if hbo['movies'] or hbo['tv']: 
            m3 += format_msg("HBO MAX", hbo, limit=5)
        
        amz = fetch_rankings(browser, "amazon-prime", "world")
        if amz['movies'] or amz['tv']: 
            m3 += format_msg("AMAZON PRIME", amz, limit=5)
            
        app = fetch_rankings(browser, "apple-tv", "world")
        if app['movies'] or app['tv']:
            m3 += format_msg("APPLE TV+", app, limit=5)
        
        send_telegram(m3)
        
        browser.close()
        print("--- 완료 ---")

if __name__ == "__main__":
    main()

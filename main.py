import os
import time
import datetime
import requests # 텔레그램 전송용
from bs4 import BeautifulSoup
from curl_cffi import requests as curl_requests # 🚨 클라우드플레어 우회 전용!

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

# 3. 데이터 수집 함수 (curl_cffi 활용 초고속 우회)
def fetch_rankings(platform, loc="world"):
    if platform == "hbo-max":
        p_ids = ["hbo", "max", "hbo-max"]
    else:
        p_ids = [platform]
        
for pid in p_ids:
        url = f"https://flixpatrol.com/top10/{pid}/{loc}/"
        print(f"[{platform}] 접속 시도: {url}")
        
        try:
            # 💡 사람 브라우저처럼 보이기 위한 헤더 추가
            headers = {
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            }
            # 🚨 chrome110 대신 최신 버전인 chrome124로 위장!
            res = curl_requests.get(url, impersonate="chrome124", headers=headers, timeout=15)
            
            if res.status_code != 200:
                print(f"⚠️ {pid} 응답 에러 (코드: {res.status_code})")
                continue
                
            soup = BeautifulSoup(res.text, 'html.parser')
            movies = []
            tv = []

            # 2. FlixPatrol 실시간 표(Table) 직관적 파싱
            tables = soup.find_all('table')
            
            for idx, tbl in enumerate(tables):
                parsed_list = []
                for row in tbl.find_all('tr'):
                    cols = row.find_all('td')
                    if len(cols) >= 2:
                        rank_txt = cols[0].get_text(strip=True).replace(".", "")
                        if rank_txt.isdigit():
                            rank = int(rank_txt)
                            link = row.find('a')
                            if link:
                                href = link.get('href', '')
                                slug = href.split('/')[-2] if '/' in href else ""
                                raw_title = link.get_text(strip=True) or link.get('title', '')
                                title = KOR_MAP.get(slug, raw_title)
                                if title:
                                    parsed_list.append(f"{rank}위 {title}")
                            if len(parsed_list) == 10:
                                break
                
                # 첫 번째 표(idx=0)는 영화, 두 번째 표(idx=1)는 TV쇼로 담기
                if parsed_list:
                    if idx == 0 and not movies:
                        movies = parsed_list
                    elif idx == 1 and not tv:
                        tv = parsed_list

            if movies or tv:
                return {"movies": movies, "tv": tv}

        except Exception as e:
            print(f"⚠️ 에러 ({pid}): {e}")
            
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
    
    # [1] NETFLIX
    n_world = fetch_rankings("netflix", "world")
    n_kr = fetch_rankings("netflix", "south-korea")
    
    m1 = f"🏆 **[1/3] NETFLIX 실시간 랭킹 ({time_str})**\n━━━━━━━━━━━━━━━━━━\n\n"
    m1 += format_msg("NETFLIX Global", n_world, limit=10)
    m1 += format_korea_ranking(n_kr)
    m1 += "🔗 [상세보기](https://flixpatrol.com/top10/netflix/)\n"
    
    send_telegram(m1)
    time.sleep(2)
    
    # [2] DISNEY+
    d_world = fetch_rankings("disney", "world")
    d_kr = fetch_rankings("disney", "south-korea") 
    
    m2 = f"🏆 **[2/3] DISNEY+ 실시간 랭킹 ({time_str})**\n━━━━━━━━━━━━━━━━━━\n\n"
    m2 += format_msg("DISNEY+", d_world, limit=10)
    m2 += format_korea_ranking(d_kr) 
    m2 += "🔗 [상세보기](https://flixpatrol.com/top10/disney/)\n" 
    
    send_telegram(m2)
    time.sleep(2)
    
    # [3] 기타 (HBO MAX, AMAZON, APPLE)
    m3 = f"🏆 **[3/3] 기타 OTT 통합 랭킹 ({time_str})**\n━━━━━━━━━━━━━━━━━━\n\n"
    
    hbo = fetch_rankings("hbo-max", "world")
    if hbo['movies'] or hbo['tv']: 
        m3 += format_msg("HBO MAX", hbo, limit=5)
    
    amz = fetch_rankings("amazon-prime", "world")
    if amz['movies'] or amz['tv']: 
        m3 += format_msg("AMAZON PRIME", amz, limit=5)
        
    app = fetch_rankings("apple-tv", "world")
    if app['movies'] or app['tv']:
        m3 += format_msg("APPLE TV+", app, limit=5)
    
    send_telegram(m3)
    
    print("--- 완료 ---")

if __name__ == "__main__":
    main()

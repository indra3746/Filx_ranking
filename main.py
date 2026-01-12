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

# 3. 데이터 수집
def fetch_rankings(platform, loc="world"):
    # HBO의 경우 hbo와 max 둘 다 시도해보기 위한 리스트
    if platform == "hbo-max":
        p_ids = ["hbo", "max"] 
    else:
        p_ids = [platform]
        
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Referer': 'https://flixpatrol.com/'
    }

    for pid in p_ids:
        # 날짜 없이 베이스 URL 사용 (자동 리다이렉트)
        url = f"https://flixpatrol.com/top10/{pid}/{loc}/"
        print(f"[{platform}] 접속 시도: {url}")
        
        try:
            res = requests.get(url, headers=headers, timeout=20)
            if res.status_code != 200:
                print(f"⚠️ {pid} 경로 응답 없음 ({res.status_code})")
                continue
            
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # 무차별 파싱 (모든 행 조사)
            all_rows = soup.find_all('tr')
            
            movies = []
            tv = []
            current_list = []
            list_count = 0 
            
            for row in all_rows:
                cols = row.find_all('td')
                if len(cols) >= 2:
                    rank_txt = cols[0].get_text(strip=True).replace(".", "")
                    if rank_txt.isdigit():
                        rank = int(rank_txt)
                        
                        # 1위가 다시 나오면 리스트 분리
                        if rank == 1 and current_list:
                            if list_count == 0: movies = current_list[:]
                            elif list_count == 1: tv = current_list[:]
                            current_list = []
                            list_count += 1
                        
                        # 제목 추출
                        link = row.find('a')
                        title_txt = "-"
                        if link:
                            slug = link.get('href', '').split('/')[-2]
                            raw = link.get_text(strip=True) or link.get('title') or slug.replace('-', ' ').title()
                            title_txt = KOR_MAP.get(slug, raw)
                        else:
                            title_txt = cols[1].get_text(strip=True)

                        # [수정] 변동폭 제거하고 순위와 제목만 저장
                        current_list.append(f"{rank}위 {title_txt}")

            # 마지막 뭉치 처리
            if current_list:
                if list_count == 0: movies = current_list
                elif list_count == 1: tv = current_list
                
            # 데이터가 하나라도 있으면 반환 (성공)
            if movies or tv:
                return {"movies": movies, "tv": tv}

        except Exception as e:
            print(f"⚠️ 에러 ({pid}): {e}")
            
    return {"movies": [], "tv": []}

# 4. 메시지 포맷팅 (limit 옵션 추가)
def format_msg(name, data, limit=10):
    msg = f"🎬 **{name}**\n"
    has_data = False
    
    # 영화
    if data['movies']:
        msg += f" 🌎 글로벌 TOP {limit} (영화)\n"
        # 리스트 슬라이싱으로 개수 제한
        msg += "\n".join([f" {x}" for x in data['movies'][:limit]]) + "\n\n"
        has_data = True
        
    # TV 쇼
    if data['tv']:
        msg += f" 🌎 글로벌 TOP {limit} (TV 쇼)\n"
        msg += "\n".join([f" {x}" for x in data['tv'][:limit]]) + "\n\n"
        has_data = True
        
    if not has_data:
        msg += " (데이터 없음)\n\n"
    return msg

# 5. 메인 로직
def main():
    # 시간 설정
    now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9)
    time_str = now.strftime("%y.%m.%d %H:%M")
    
    print(f"--- 실행 ({time_str}) ---")
    
    # [1] NETFLIX
    n_world = fetch_rankings("netflix", "world")
    n_kr = fetch_rankings("netflix", "south-korea")
    
    m1 = f"🏆 **[1/3] NETFLIX 실시간 랭킹 ({time_str})**\n━━━━━━━━━━━━━━━━━━\n\n"
    m1 += format_msg("NETFLIX Global", n_world, limit=10)
    
    # 넷플릭스 한국 (영화/TV 모두 표시)
    if n_kr['movies'] or n_kr['tv']:
         m1 += " 🇰🇷 **한국 TOP 10**\n"
         if n_kr['movies']: 
             m1 += " [영화]\n" + "\n".join([f" {x}" for x in n_kr['movies'][:10]]) + "\n"
         if n_kr['tv']: 
             m1 += " [TV 쇼]\n" + "\n".join([f" {x}" for x in n_kr['tv'][:10]]) + "\n"
         
    send_telegram(m1)
    time.sleep(3)
    
    # [2] DISNEY+
    d_world = fetch_rankings("disney", "world")
    m2 = f"🏆 **[2/3] DISNEY+ 실시간 랭킹 ({time_str})**\n━━━━━━━━━━━━━━━━━━\n\n"
    m2 += format_msg("DISNEY+", d_world, limit=10)
    send_telegram(m2)
    time.sleep(3)
    
    # [3] 기타 (5위까지만 표시)
    m3 = f"🏆 **[3/3] 기타 OTT 통합 랭킹 ({time_str})**\n━━━━━━━━━━━━━━━━━━\n\n"
    
    # HBO MAX (hbo 또는 max 시도)
    hbo = fetch_rankings("hbo-max", "world")
    if hbo['movies'] or hbo['tv']: 
        m3 += format_msg("HBO MAX", hbo, limit=5) # 5위 제한
    
    # AMAZON PRIME
    amz = fetch_rankings("amazon-prime", "world")
    if amz['movies'] or amz['tv']: 
        m3 += format_msg("AMAZON PRIME", amz, limit=5) # 5위 제한
        
    # APPLE TV+ (추가 요청에 대비해 미리 포함)
    app = fetch_rankings("apple-tv", "world")
    if app['movies'] or app['tv']:
        m3 += format_msg("APPLE TV+", app, limit=5)
    
    send_telegram(m3)
    print("--- 완료 ---")

if __name__ == "__main__":
    main()

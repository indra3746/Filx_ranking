import requests
from bs4 import BeautifulSoup
import datetime
import os
import time
import random

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

# 3. 데이터 수집 (무차별 파싱 모드)
def fetch_rankings(platform, loc="world"):
    # 플랫폼 ID 보정
    p_id = "hbo" if platform == "hbo-max" else platform
    url = f"https://flixpatrol.com/top10/{p_id}/{loc}/"
    
    # [핵심] 리얼한 브라우저 헤더 (차단 방지)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://flixpatrol.com/',
        'Upgrade-Insecure-Requests': '1'
    }

    print(f"[{platform}] 접속: {url}")
    
    try:
        # 접속 시도
        res = requests.get(url, headers=headers, timeout=20)
        
        # 404면 빈 값 반환
        if res.status_code == 404:
            print(f"⚠️ {platform} 404 Not Found")
            return {"movies": [], "tv": []}
            
        soup = BeautifulSoup(res.text, 'html.parser')

        # [핵심 로직 변경] 특정 클래스 찾지 않고 모든 tr(행)을 뒤짐
        all_rows = soup.find_all('tr')
        
        movies = []
        tv = []
        
        # 임시 저장소
        current_list = []
        
        # 데이터가 뭉텅이로 있을 때 구분하기 위한 플래그
        # 보통 영화 리스트가 먼저 나오고, 그 다음 TV 리스트가 나옴
        list_count = 0 
        
        for row in all_rows:
            cols = row.find_all('td')
            # 유효한 랭킹 행인지 검사 (열이 2개 이상이고, 첫 열이 숫자여야 함)
            if len(cols) >= 2:
                rank_txt = cols[0].get_text(strip=True).replace(".", "")
                if rank_txt.isdigit():
                    rank = int(rank_txt)
                    
                    # 1위가 다시 나오면 새로운 리스트가 시작된 것임
                    if rank == 1 and current_list:
                        if list_count == 0:
                            movies = current_list[:] # 첫번째 뭉치는 영화
                        elif list_count == 1:
                            tv = current_list[:]     # 두번째 뭉치는 TV
                        current_list = [] # 초기화
                        list_count += 1
                    
                    # 제목 추출
                    link = row.find('a')
                    title_txt = "-"
                    if link:
                        slug = link.get('href', '').split('/')[-2]
                        # 텍스트가 없으면 title 속성, 그것도 없으면 슬러그
                        raw = link.get_text(strip=True) or link.get('title') or slug.replace('-', ' ').title()
                        title_txt = KOR_MAP.get(slug, raw)
                    else:
                        # 링크가 없는 경우 텍스트라도 가져옴
                        title_txt = cols[1].get_text(strip=True)

                    # 변동폭
                    change_txt = "-"
                    if len(cols) > 1:
                        spans = cols[1].find_all('span')
                        for span in spans:
                            stxt = span.get_text(strip=True)
                            if stxt in ['▲', '▼'] or stxt.isdigit() or 'n/a' in stxt:
                                change_txt = stxt.replace('n/a', '신규')

                    # 결과 추가
                    current_list.append(f"{rank}위 {title_txt} | {change_txt}")

        # 마지막 뭉치 처리
        if current_list:
            if list_count == 0: movies = current_list
            elif list_count == 1: tv = current_list
            
        # 만약 영화/TV 구분이 안 되고 하나만 뭉쳐 있다면?
        # 보통 넷플릭스 월드는 영화/TV가 다 있음.
        # 하나만 있으면 일단 movies에 넣음.
        
        return {"movies": movies[:10], "tv": tv[:10]}

    except Exception as e:
        print(f"⚠️ 에러 ({platform}): {e}")
        return {"movies": [], "tv": []}

# 4. 메시지 생성
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
        msg += " (데이터 없음)\n\n"
    return msg

# 5. 메인 로직
def main():
    # DeprecationWarning 방지용 시간 설정
    now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9)
    time_str = now.strftime("%y.%m.%d %H:%M")
    
    print(f"--- 실행 ({time_str}) ---")
    
    # 1. 넷플릭스
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
    
    # 2. 디즈니
    d_world = fetch_rankings("disney", "world")
    m2 = f"🏆 **[2/3] DISNEY+ 실시간 랭킹 ({time_str})**\n━━━━━━━━━━━━━━━━━━\n\n"
    m2 += format_msg("DISNEY+", d_world)
    send_telegram(m2)
    time.sleep(3)
    
    # 3. 기타
    # HBO 404가 계속 뜬다면 URL 문제일 수 있으니 hbo-max 원복 시도
    # hbo가 안되면 amazon이라도 보내야 함
    
    m3 = f"🏆 **[3/3] 기타 OTT 통합 랭킹 ({time_str})**\n━━━━━━━━━━━━━━━━━━\n\n"
    
    # HBO (hbo가 404면 hbo-max로도 시도해보는 로직은 fetch 함수 안에서 처리 필요하지만
    # 여기선 일단 hbo로 시도. 안되면 빈칸)
    hbo = fetch_rankings("hbo", "world") 
    if hbo['movies'] or hbo['tv']: m3 += format_msg("HBO MAX", hbo)
    
    amz = fetch_rankings("amazon-prime", "world")
    if amz['movies'] or amz['tv']: m3 += format_msg("AMAZON PRIME", amz)
    
    send_telegram(m3)
    print("--- 완료 ---")

if __name__ == "__main__":
    main()

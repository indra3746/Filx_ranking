import requests
from bs4 import BeautifulSoup
import datetime
import os
import time

# 한글 제목 매핑
KOR_MAP = {
    "his-hers": "히스 앤 허스",
    "people-we-meet-on-vacation": "우리의 열 번째 여름",
    "the-ugly": "얼굴",
    "your-letter": "연의 편지",
    "the-great-flood": "대홍수",
    "tron-ares": "트론: 아레스",
    "made-in-korea": "메이드 인 코리아",
    "culinary-class-wars": "흑백요리사",
    "squid-game": "오징어 게임"
}

def get_date_str():
    # 한국 시간 기준 날짜 생성 (URL용)
    now = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
    return now.strftime("%Y-%m-%d")

def fetch_daily_rankings(platform, loc="world"):
    # 1. 플랫폼 ID 보정
    p_id = "hbo" if platform == "hbo-max" else platform
    
    # 2. 날짜 기반 통합 URL 생성 (404 방지)
    date_str = get_date_str()
    url = f"https://flixpatrol.com/top10/{p_id}/{loc}/{date_str}/"
    
    print(f"접속 시도: {url}") # 디버깅용 로그
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=30)
        if res.status_code != 200:
            print(f"❌ 접속 실패 ({res.status_code}): {url}")
            return {"movies": [], "tv": []}
        
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 3. 데이터 파싱 (한 페이지 내에서 영화/TV 분리)
        # FlixPatrol은 보통 첫 번째 테이블이 영화, 두 번째가 TV쇼이거나, 
        # h2 헤더 순서대로 배치됩니다.
        
        # 모든 랭킹 리스트 컨테이너 찾기
        groups = soup.find_all('div', class_='content-block')
        if not groups:
            # 구조가 다를 경우 테이블 그룹으로 시도
            groups = soup.find_all('tbody', class_='table-group')
            
        movies_data = []
        tv_data = []
        
        # 순서대로 영화 -> TV라고 가정하고 추출 (일반적인 패턴)
        # 만약 헤더가 있다면 헤더 텍스트로 구분
        
        full_lists = []
        # 테이블 추출 로직
        for table in soup.select('tbody.table-group'):
            rows = table.find_all('tr')
            extracted = []
            for row in rows[:10]: # TOP 10만
                tds = row.find_all('td')
                if len(tds) < 2: continue
                
                # 순위
                rank = tds[0].get_text(strip=True).replace(".", "")
                
                # 제목
                title_link = row.find('a', href=True)
                title = "-"
                if title_link:
                    slug = title_link['href'].split('/')[-2]
                    raw_title = title_link.get('title') or title_link.get_text(strip=True)
                    if raw_title.replace(".", "").isdigit():
                        raw_title = slug.replace('-', ' ').title()
                    title = KOR_MAP.get(slug, raw_title)
                
                # 변동
                change = "-"
                if len(tds) > 1:
                    change_span = tds[1].select_one('span')
                    if change_span:
                        change = change_span.get_text(strip=True).replace('n/a', '신규')
                
                extracted.append(f"{rank}위 {title} | {change}")
            full_lists.append(extracted)
            
        # 데이터 분배 (리스트가 2개 이상이면 0:영화, 1:TV로 간주)
        if len(full_lists) >= 1:
            movies_data = full_lists[0]
        if len(full_lists) >= 2:
            tv_data = full_lists[1]
            
        return {"movies": movies_data, "tv": tv_data}

    except Exception as e:
        print(f"⚠️ 에러 발생: {e}")
        return {"movies": [], "tv": []}

def format_message(name, data):
    msg = f"🎬 **{name}**\n"
    
    if data['movies']:
        msg += " 🌎 글로벌 TOP 10 (영화)\n"
        for item in data['movies']:
            msg += f" {item}\n"
        msg += "\n"
        
    if data['tv']:
        msg += " 🌎 글로벌 TOP 10 (TV 쇼)\n"
        for item in data['tv']:
            msg += f" {item}\n"
            
    if not data['movies'] and not data['tv']:
        msg += " (데이터 수집 실패 또는 랭킹 없음)\n"
        
    return msg + "\n"

def send_telegram(text):
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("CHAT_ID")
    if token and chat_id:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage", 
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
        )

def main():
    # 시간 표시
    kst_now = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
    time_str = kst_now.strftime("%y.%m.%d %H:%M")
    
    print("--- 데이터 수집 시작 ---")
    
    # 1. 넷플릭스
    netflix_data = fetch_daily_rankings("netflix", "world")
    # 한국 데이터는 별도 호출 필요 (구조 동일)
    netflix_kr = fetch_daily_rankings("netflix", "south-korea")
    
    msg1 = f"🏆 **[1/3] NETFLIX 실시간 랭킹 ({time_str})**\n━━━━━━━━━━━━━━━━━━\n\n"
    msg1 += format_message("NETFLIX Global", netflix_data)
    msg1 += " 🇰🇷 **한국 TOP 10 (통합)**\n" # 한국은 보통 통합으로 나옴
    for item in netflix_kr['movies'][:5]: msg1 += f" {item}\n" 
    
    send_telegram(msg1)
    time.sleep(3)
    
    # 2. 디즈니
    disney_data = fetch_daily_rankings("disney", "world")
    msg2 = f"🏆 **[2/3] DISNEY+ 실시간 랭킹 ({time_str})**\n━━━━━━━━━━━━━━━━━━\n\n"
    msg2 += format_message("DISNEY+", disney_data)
    send_telegram(msg2)
    time.sleep(3)
    
    # 3. 기타 플랫폼
    msg3 = f"🏆 **[3/3] 기타 OTT 통합 랭킹 ({time_str})**\n━━━━━━━━━━━━━━━━━━\n\n"
    
    # HBO
    hbo_data = fetch_daily_rankings("hbo-max", "world")
    if hbo_data['movies'] or hbo_data['tv']:
        msg3 += format_message("HBO MAX", hbo_data)
        
    # Amazon
    amz_data = fetch_daily_rankings("amazon-prime", "world")
    if amz_data['movies'] or amz_data['tv']:
         msg3 += format_message("AMAZON PRIME", amz_data)
         
    send_telegram(msg3)
    print("--- 전송 완료 ---")

if __name__ == "__main__":
    main()

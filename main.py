import requests
from bs4 import BeautifulSoup
import datetime
import os
import time

# 한글 매핑 DB
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
    "the-pitt": "더 피트"
}

def fetch_rankings(platform, loc="world"):
    # 1. 플랫폼 ID 보정 (HBO MAX -> hbo)
    p_id = "hbo" if platform == "hbo-max" else platform
    
    # 2. 날짜 지정 없이 'today' 경로 사용 (404 방지 핵심)
    url = f"https://flixpatrol.com/top10/{p_id}/{loc}/today/"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    print(f"📡 접속 시도: {url}") # 로그 확인용
    
    try:
        res = requests.get(url, headers=headers, timeout=30)
        # 404가 뜨면 데이터가 없는 것이므로 빈 리스트 반환
        if res.status_code != 200:
            print(f"❌ 실패 ({res.status_code}): {url}")
            return {"movies": [], "tv": []}
            
        soup = BeautifulSoup(res.text, 'html.parser')
        
        movies = []
        tv = []
        
        # 3. HTML 구조 분석 (영화/TV 자동 분류)
        # 페이지 내의 모든 'content-block'을 찾고, 그 앞의 헤더(h2)를 확인
        blocks = soup.find_all('div', class_='content-block')
        
        # 블록이 감지되지 않으면 테이블 그룹으로 시도 (구조 변경 대응)
        if not blocks:
            # 테이블 순서대로 0:영화, 1:TV로 가정
            tables = soup.select('tbody.table-group')
            for i, table in enumerate(tables):
                data = parse_table(table)
                if i == 0: movies = data
                elif i == 1: tv = data
        else:
            # 헤더 텍스트로 명확히 구분
            for block in blocks:
                header = block.find_previous('h2')
                category = header.get_text(strip=True).lower() if header else ""
                
                table = block.find('tbody', class_='table-group')
                if not table: continue
                
                parsed_data = parse_table(table)
                
                if 'movie' in category or 'film' in category:
                    movies = parsed_data
                elif 'tv' in category or 'show' in category or 'series' in category:
                    tv = parsed_

import requests
from bs4 import BeautifulSoup
import datetime

# 1. 공식 제목 매핑 데이터셋 (지속적으로 업데이트 가능)
OFFICIAL_KOR_TITLES = {
    "People We Meet on Vacation": "우리의 열 번째 여름",
    "Stranger Things": "기묘한 이야기",
    "Culinary Class Wars": "흑백요리사: 요리 계급 전쟁",
    "His & Hers": "히스 앤 허스",
    "Run Away": "런 어웨이",
    "Outer Banks": "아웃터 뱅크스",
    "Black Mirror": "검은 거울",
    "TRON: Ares": "트론: 아레스",
    "Avatar: The Way of Water": "아바타: 물의 길",
    "Elemental": "엘리멘탈",
    "The Light Shop": "조명가게",
    "Moving": "무빙",
    "Jujutsu Kaisen": "주술회전",
    "House of the Dragon": "하우스 오브 드래곤",
    "Ted Lasso": "테드 래소",
    "Badlands": "프레데터: 배드랜즈",
    "F1": "F1 (브래드 피트 주연)"
}

def get_official_title(eng_title):
    """영문 제목을 공식 한글 제목으로 변환"""
    return OFFICIAL_KOR_TITLES.get(eng_title, eng_title)

def fetch_flix_ranking(platform, location="world", limit=10):
    """FlixPatrol에서 특정 플랫폼/지역의 순위 데이터를 긁어옴"""
    url = f"https://flixpatrol.com/top10/{platform}/{location}/today/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        rows = soup.select('tr.table-group')
        
        extracted_data = []
        for row in rows[:limit]:
            cols = row.find_all('td')
            if len(cols) >= 3:
                rank = cols[0].text.strip()
                eng_title = cols[2].text.strip()
                index_val = cols[3].text.strip() if len(cols) > 3 else "-"
                
                kor_title = get_official_title(eng_title)
                extracted_data.append({
                    "rank": rank,
                    "title": f"{kor_title} ({eng_title})",
                    "index": index_val
                })
        return extracted_data

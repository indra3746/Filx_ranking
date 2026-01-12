import requests
from bs4 import BeautifulSoup
import datetime
import os

# 공식 한글 제목 매핑 데이터셋
OFFICIAL_KOR_TITLES = {
    "People We Meet on Vacation": "우리의 열 번째 여름",
    "Stranger Things": "기묘한 이야기",
    "Culinary Class Wars": "흑백요리사: 요리 계급 전쟁",
    "His & Hers": "히스 앤 허스",
    "Run Away": "런 어웨이",
    "Outer Banks": "아웃터 뱅크스",
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
    return OFFICIAL_KOR_TITLES.get(eng_title, eng_title)

def fetch_flix_ranking(platform, location="world", limit=10):
    url = f"https://flixpatrol.com/top10/{platform}/{location}/today/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        rows = soup.select('tr.table-group')
        data = []
        for row in rows[:limit]:
            cols = row.find_all('td')
            if len(cols) >= 3:
                rank = cols[0].text.strip()
                eng_title = cols[2].text.strip()
                idx = cols[3].text.strip() if len(cols) > 3 else "-"
                data.append({"rank": rank, "title": f"{get_official_title(eng_title)} ({eng_title})", "index": idx})
        return data
    except:
        return []

def send_telegram_msg(text):
    # GitHub Secrets에 저장된 토큰과 ID 사용
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if token and chat_id:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
        requests.post(url, json=payload)

def run_report():
    now = datetime.datetime.now().strftime("%Y.%m.%d %H:%M")
    report = f"🎬 **OTT 통합 실시간 랭킹 리포트 ({now})**\n\n"
    
    configs = [
        {"id": "netflix", "name": "NETFLIX", "limits": {"world": 10, "south-korea": 10}},
        {"id": "disney", "name": "DISNEY+", "limits": {"world": 10, "south-korea": 10}},
        {"id": "apple-tv", "name": "APPLE TV+", "limits": {"world": 3}},
        {"id": "amazon-prime", "name": "AMAZON", "limits": {"world": 3}},
        {"id": "hbo", "name": "HBO MAX", "limits": {"world": 3}}
    ]

    for cfg in configs:
        report += f"### 📦 {cfg['name']}\n"
        world = fetch_flix_ranking(cfg['id'], "world", cfg['limits']['world'])
        if world:
            report += "| 구분 | 순위 | 제목 (한글명) | Index |\n| :--- | :--- | :--- | :--- |\n"
            for itm in world:
                report += f"| 글로벌 | {itm['rank']} | {itm['title']} | {itm['index']} |\n"
        
        if "south-korea" in cfg['limits']:
            korea = fetch_flix_ranking(cfg['id'], "south-korea", cfg['limits']['south-korea'])
            for itm in korea:
                report += f"| 한국 | {itm['rank']} | {itm['title']} | - |\n"
        report += "\n"
    
    send_telegram_msg(report)

if __name__ == "__main__":
    run_report()

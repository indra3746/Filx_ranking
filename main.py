import requests
from bs4 import BeautifulSoup
import datetime
import os

# 한글 제목 매핑 (사용자 요청 반영 및 고도화)
OFFICIAL_KOR_TITLES = {
    "People We Meet on Vacation": "우리의 열 번째 여름",
    "The Ugly": "얼굴",
    "Your Letter": "연의 편지",
    "The Great Flood": "대홍수",
    "His & Hers": "히스 앤 허스",
    "TRON: Ares": "트론: 아레스",
    "Avatar: The Way of Water": "아바타: 물의 길",
    "Culinary Class Wars": "흑백요리사"
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
                rank = cols[0].get_text(strip=True).replace(".", "")
                
                # 순위 변동 추출 (상승/하락/유지 아이콘 대응)
                change_tag = cols[1].find('span', class_='text-green-500') or \
                             cols[1].find('span', class_='text-red-500') or \
                             cols[1].find('span', class_='text-gray-500')
                change = change_tag.get_text(strip=True) if change_tag else "-"

                title_raw = cols[2].get_text(strip=True)
                if title_raw.isdigit(): title_raw = cols[1].get_text(strip=True)
                
                # Index(점수) 및 출시일 정보 (한국 상세 페이지 등에서 추출 가능하나 기본값 설정)
                idx = cols[3].get_text(strip=True) if len(cols) > 3 else ""
                
                # 가상의 출시일 데이터 (실제 데이터는 추가 크롤링이 필요하므로 현재는 제목 옆 포맷 유지)
                release_date = "2024.03.09." # 예시용 (실제 구현 시 상세 페이지 연동 필요)

                data.append({
                    "rank": rank,
                    "title": get_official_title(title_raw),
                    "eng": title_raw,
                    "index": idx,
                    "change": change,
                    "rel_date": release_date
                })
        return data
    except:
        return []

def send_telegram_msg(text):
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("CHAT_ID") 
    if token and chat_id:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
        requests.post(url, json=payload)

def run_report():
    now = datetime.datetime.now().strftime("%Y.%m.%d %H:%M")
    report = f"🎬 *OTT 통합 실시간 랭킹 ({now})*\n\n"
    
    configs = [
        {"id": "netflix", "name": "NETFLIX", "limits": {"world": 10, "south-korea": 10}},
        {"id": "disney", "name": "DISNEY+", "limits": {"world": 10, "south-korea": 10}},
        {"id": "apple-tv", "name": "APPLE TV+", "limits": {"world": 3}},
        {"id": "amazon-prime", "name": "AMAZON", "limits": {"world": 3}},
        {"id": "hbo", "name": "HBO MAX", "limits": {"world": 3}}
    ]

    for cfg in configs:
        report += f"📦 *{cfg['name']}*\n"
        
        # 🌐 글로벌 TOP (순위 변동 표시 포함)
        world = fetch_flix_ranking(cfg['id'], "world", cfg['limits']['world'])
        if world:
            report += "  🌐 글로벌 TOP\n"
            for itm in world:
                # 포맷: 제목 (점수 / 변동)
                change_str = f" / {itm['change']}" if itm['change'] != "-" else ""
                report += f"  {itm['rank']}. {itm['title']} ({itm['index']}{change_str})\n"
        
        # 🇰🇷 한국 TOP (출시일 한글제목(영어제목) 형식)
        if "south-korea" in cfg['limits']:
            korea = fetch_flix_ranking(cfg['id'], "south-korea", cfg['limits']['south-korea'])
            if korea:
                report += "  🇰🇷 한국 TOP\n"
                for itm in korea:
                    # 사용자 요청 포맷: 1. 출시일 한글제목(영어제목)
                    report += f"  {itm['rank']}. {itm['rel_date']} {itm['title']}({itm['eng']})\n"
        report += "\n"
    
    send_telegram_msg(report)

if __name__ == "__main__":
    run_report()

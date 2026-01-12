import requests
from bs4 import BeautifulSoup
import datetime
import os

# 콘텐츠 데이터베이스 (연도 2자리 포맷 반영)
CONTENT_DB = {
    "HIS & HERS": {"kor": "히스 앤 허스", "date": "26.01.08."},
    "People We Meet on Vacation": {"kor": "우리의 열 번째 여름", "date": "26.01.08."},
    "The Ugly": {"kor": "얼굴", "date": "26.01.09."},
    "Your Letter": {"kor": "연의 편지", "date": "26.01.12."},
    "The Great Flood": {"kor": "대홍수", "date": "26.01.09."},
    "Stranger Things": {"kor": "기묘한 이야기", "date": "16.07.15."},
    "Avatar: The Way of Water": {"kor": "아바타: 물의 길", "date": "22.12.16."},
    "TRON: Ares": {"kor": "트론: 아레스", "date": "25.12.25."},
    "The Light Shop": {"kor": "조명가게", "date": "26.01.12."}
}

def get_content_info(eng_title):
    info = CONTENT_DB.get(eng_title, {"kor": eng_title, "date": "26.01.01."})
    return info['kor'], info['date']

def fetch_data(platform, loc="world", limit=10):
    url = f"https://flixpatrol.com/top10/{platform}/{loc}/today/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        rows = soup.select('tr.table-group')
        data = []
        for row in rows[:limit]:
            tds = row.find_all('td')
            if len(tds) < 3: continue
            rank = tds[0].get_text(strip=True).replace(".", "")
            change = "-"
            change_span = tds[1].select_one('span')
            if change_span:
                txt = change_span.get_text(strip=True)
                if any(x in txt for x in ['▲', '▼', 'n/a']): change = txt.replace('n/a', '신규')
            title_raw = tds[2].get_text(strip=True)
            idx = tds[3].get_text(strip=True) if len(tds) > 3 else "0"
            kor, rel_date = get_content_info(title_raw)
            data.append({"rank": rank, "change": change, "title": kor, "eng": title_raw, "idx": idx, "date": rel_date})
        return data
    except: return []

def format_section(cfg):
    msg = f"🎬 **{cfg['name']}**\n"
    
    # 글로벌 섹션 (🌎 이모지 + 한 줄 띄움)
    world = fetch_data(cfg['id'], "world", cfg.get('lim', 10))
    if world:
        msg += f" 🌎 **글로벌 TOP {cfg.get('lim', 10)}**\n\n"
        for i in world:
            msg += f" {i['rank']}. {i['title']} | {i['idx']} ┃ {i['change']} ┃ {i['date']}\n"
    
    # 한국 섹션 (🇰🇷 이모지 + 한 줄 띄움)
    if cfg.get('korea'):
        korea = fetch_data(cfg['id'], "south-korea", 10)
        if korea:
            msg += f"\n 🇰🇷 **한국 TOP 10**\n\n"
            for i in korea:
                msg += f" {i['rank']}. {i['title']} ({i['eng']}) | {i['idx']} ┃ {i['change']} ┃ {i['date']}\n"
    return msg + "\n"

def send_telegram(text):
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("CHAT_ID")
    if token and chat_id:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})

def main():
    # 날짜 포맷 수정 (2026 -> 26)
    now = datetime.datetime.now().strftime("%y.%m.%d %H:%M")
    
    m1 = f"🏆 **OTT 통합 랭킹 [1/2] ({now})**\n━━━━━━━━━━━━━━━━━━\n\n"
    m1 += format_section({"id": "netflix", "name": "NETFLIX", "korea": True})
    m1 += format_section({"id": "disney", "name": "DISNEY+", "korea": True})
    send_telegram(m1)
    
    m2 = f"🏆 **OTT 통합 랭킹 [2/2] ({now})**\n━━━━━━━━━━━━━━━━━━\n\n"
    for p in [{"id": "apple-tv", "name": "APPLE TV+", "lim": 5}, 
              {"id": "amazon-prime", "name": "AMAZON", "lim": 5}, 
              {"id": "hbo", "name": "HBO MAX", "lim": 5}]:
        m2 += format_section(p)
    send_telegram(m2)

if __name__ == "__main__":
    main()

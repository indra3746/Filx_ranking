import os
import sys
import time
import datetime
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor

# 1. 텔레그램 전송 함수
def send_telegram(text):
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("CHAT_ID")
    if token and chat_id and len(text) > 10:
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            requests.post(url, json={
                "chat_id": chat_id, 
                "text": text, 
                "parse_mode": "HTML", 
                "disable_web_page_preview": True
            })
        except Exception as e:
            print(f"전송 실패: {e}")

# 2. 데이터 수집 함수 (ScraperAPI + render=true 우회)
def fetch_rankings(platform, loc="world"):
    scraper_api_key = os.environ.get("SCRAPER_API_KEY")
    
    if platform == "hbo-max":
        p_ids = ["max", "hbo"]
    else:
        p_ids = [platform]

    for pid in p_ids:
        target_url = f"https://flixpatrol.com/top10/{pid}/{loc}/"
        print(f"[{platform}] ScraperAPI 접속 시도: {target_url}")
        
        for attempt in range(3):
            try:
                # 💡 render: 'true'를 추가하여 Cloudflare 봇 차단을 완벽 우회합니다.
                payload = {
                    'api_key': scraper_api_key, 
                    'url': target_url,
                    'render': 'true'
                }
                res = requests.get('http://api.scraperapi.com', params=payload, timeout=60)
                
                if res.status_code == 200:
                    soup = BeautifulSoup(res.text, 'html.parser')
                    movies, tv = [], []

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
                                        raw_title = link.get_text(strip=True) or link.get('title', '')
                                        title = raw_title.replace("<", "&lt;").replace(">", "&gt;")
                                        if title:
                                            parsed_list.append(f"{rank}위 {title}")
                                    if len(parsed_list) == 10:
                                        break
                        
                        if parsed_list:
                            if idx == 0 and not movies: movies = parsed_list
                            elif idx == 1 and not tv: tv = parsed_list

                    if movies or tv:
                        return {"movies": movies, "tv": tv}
                    break
                elif res.status_code == 500:
                    print(f"⚠️ {pid} 서버 일시 장애(500). ({attempt+1}/3 재시도 중...)")
                    time.sleep(3)
                else:
                    print(f"⚠️ {pid} 응답 에러 (코드: {res.status_code})")
                    break

            except Exception as e:
                print(f"⚠️ 에러 ({pid}): {e}")
                time.sleep(2)
            
    return {"movies": [], "tv": []}

# 3. 메시지 포맷팅
def format_msg(name, data, limit=10):
    msg = f"🎬 <b>{name}</b>\n"
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

def format_korea_ranking(data):
    msg = ""
    if data['movies'] or data['tv']:
        msg += " 🇰🇷 <b>한국 TOP 10</b>\n"
        if data['movies']:
            msg += " 🎞️ <b>영화</b>\n"
            msg += "\n".join([f" {x}" for x in data['movies'][:10]]) + "\n\n" 
        if data['tv']:
            msg += " 📺 <b>TV 쇼</b>\n"
            msg += "\n".join([f" {x}" for x in data['tv'][:10]]) + "\n\n" 
    return msg

# 4. 메인 실행 함수 (ScraperAPI 한도 고려 병렬 처리)
def main():
    now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9)
    time_str = now.strftime("%y.%m.%d %H:%M")
    
    print(f"--- ⚡ ScraperAPI 병렬 수집 시작 ({time_str}) ---")
    
    tasks = {
        "n_world": ("netflix", "world"),
        "n_kr": ("netflix", "south-korea"),
        "d_world": ("disney", "world"),
        "d_kr": ("disney", "south-korea"),
        "hbo": ("hbo-max", "world"),
        "amz": ("amazon-prime", "world"),
        "app": ("apple-tv", "world")
    }
    
    results = {}
    # ScraperAPI 동시 요청 한도(5개)에 맞춰 안전하게 병렬 처리
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_key = {
            executor.submit(fetch_rankings, platform, loc): key 
            for key, (platform, loc) in tasks.items()
        }
        for future in future_to_key:
            key = future_to_key[future]
            try:
                results[key] = future.result()
            except Exception as e:
                results[key] = {"movies": [], "tv": []}

    # [1] NETFLIX
    n_world = results["n_world"]
    n_kr = results["n_kr"]
    
    if not n_world['movies'] and not n_world['tv']:
        print("❌ NETFLIX 데이터 수집 실패! (10분 뒤 재시도 실행)")
        sys.exit(1)
        
    m1 = f"🏆 <b>[1/3] NETFLIX 실시간 랭킹 ({time_str})</b>\n━━━━━━━━━━━━━━━━━━\n\n"
    m1 += format_msg("NETFLIX Global", n_world, limit=10)
    m1 += format_korea_ranking(n_kr)
    m1 += '🔗 <a href="https://flixpatrol.com/top10/netflix/">상세보기</a>\n'
    send_telegram(m1)
    
    # [2] DISNEY+
    d_world = results["d_world"]
    d_kr = results["d_kr"]
    
    m2 = f"🏆 <b>[2/3] DISNEY+ 실시간 랭킹 ({time_str})</b>\n━━━━━━━━━━━━━━━━━━\n\n"
    m2 += format_msg("DISNEY+", d_world, limit=10)
    m2 += format_korea_ranking(d_kr)
    m2 += '🔗 <a href="https://flixpatrol.com/top10/disney/">상세보기</a>\n'
    send_telegram(m2)
    
    # [3] 기타
    hbo, amz, app = results["hbo"], results["amz"], results["app"]
    if (hbo['movies'] or hbo['tv'] or amz['movies'] or amz['tv'] or app['movies'] or app['tv']):
        m3 = f"🏆 <b>[3/3] 기타 OTT 통합 랭킹 ({time_str})</b>\n━━━━━━━━━━━━━━━━━━\n\n"
        if hbo['movies'] or hbo['tv']: m3 += format_msg("MAX (HBO)", hbo, limit=5)
        if amz['movies'] or amz['tv']: m3 += format_msg("AMAZON PRIME", amz, limit=5)
        if app['movies'] or app['tv']: m3 += format_msg("APPLE TV+", app, limit=5)
        send_telegram(m3)
        
    print("--- 완료 ---")

if __name__ == "__main__":
    main()

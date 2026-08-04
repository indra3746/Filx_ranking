import os
import sys
import time
import datetime
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

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

# 2. 무료 살아있는 프록시 IP 획득 함수
def get_free_proxies():
    print("🌐 차단 방지용 무료 프록시 IP 목록 수집 중...")
    proxy_urls = [
        "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
        "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt"
    ]
    proxies = []
    for url in proxy_urls:
        try:
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                lines = [line.strip() for line in res.text.splitlines() if ":" in line]
                proxies.extend(lines[:15]) # 상위 15개 추출
        except Exception:
            continue
    return list(set(proxies))

# 3. 데이터 수집 함수
def fetch_rankings(page, platform, loc="world"):
    if platform == "hbo-max":
        p_ids = ["max", "hbo"]
    else:
        p_ids = [platform]

    for pid in p_ids:
        target_url = f"https://flixpatrol.com/top10/{pid}/{loc}/"
        print(f"[{platform}] 우회 접속 시도: {target_url}")
        
        try:
            response = page.goto(target_url, timeout=30000, wait_until="load")
            time.sleep(2)
            
            status = response.status if response else 0
            if status == 200:
                html_content = page.content()
                soup = BeautifulSoup(html_content, 'html.parser')
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
            else:
                print(f"⚠️ {pid} 응답 코드: {status}")

        except Exception as e:
            print(f"⚠️ 에러 ({pid}): {e}")
            
    return {"movies": [], "tv": []}

# 4. 포맷팅 함수들
def format_msg(name, data, limit=10):
    msg = f"🎬 <b>{name}</b>\n"
    has_data = False
    if data['movies']:
        msg += f" 🌎 글로벌 TOP {limit} (영화)\n" + "\n".join([f" {x}" for x in data['movies'][:limit]]) + "\n\n"
        has_data = True
    if data['tv']:
        msg += f" 🌎 글로벌 TOP {limit} (TV 쇼)\n" + "\n".join([f" {x}" for x in data['tv'][:limit]]) + "\n\n"
        has_data = True
    if not has_data:
        msg += " (데이터 없음)\n\n"
    return msg

def format_korea_ranking(data):
    msg = ""
    if data['movies'] or data['tv']:
        msg += " 🇰🇷 <b>한국 TOP 10</b>\n"
        if data['movies']:
            msg += " 🎞️ <b>영화</b>\n" + "\n".join([f" {x}" for x in data['movies'][:10]]) + "\n\n" 
        if data['tv']:
            msg += " 📺 <b>TV 쇼</b>\n" + "\n".join([f" {x}" for x in data['tv'][:10]]) + "\n\n" 
    return msg

# 5. 메인 실행 함수 (프록시 체인 적용)
def main():
    now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9)
    time_str = now.strftime("%y.%m.%d %H:%M")
    
    print(f"--- 🚀 프록시 우회 수집 시작 ({time_str}) ---")
    
    proxies = get_free_proxies()
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
    success = False

    with sync_playwright() as p:
        # 프록시 목록을 하나씩 바꿔가며 403 안 뜨는 놈을 탐색
        for proxy in proxies[:10]: # 최대 10개 프록시 시도
            print(f"🔄 프록시 IP 우회 시도: http://{proxy}")
            try:
                browser = p.chromium.launch(
                    headless=True,
                    proxy={"server": f"http://{proxy}"},
                    args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-blink-features=AutomationControlled"]
                )
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                page = context.new_page()

                # 테스트로 넷플릭스 하나 수집해봄
                test_res = fetch_rankings(page, "netflix", "world")
                if test_res['movies'] or test_res['tv']:
                    print(f"✅ 프록시 접속 성공! ({proxy})")
                    results["n_world"] = test_res
                    
                    # 성공한 프록시로 나머지 전부 긁어옴
                    for key, (platform, loc) in tasks.items():
                        if key != "n_world":
                            results[key] = fetch_rankings(page, platform, loc)
                            time.sleep(1)
                    
                    browser.close()
                    success = True
                    break
                else:
                    browser.close()
            except Exception as e:
                print(f"❌ 프록시 실패 ({proxy}): {e}")
                continue

    # 텔레그램 메시지 발송
    n_world = results.get("n_world", {"movies":[], "tv":[]})
    n_kr = results.get("n_kr", {"movies":[], "tv":[]})
    
    if not success or (not n_world['movies'] and not n_world['tv']):
        print("❌ 모든 무료 프록시 실패 / 데이터 수집 실패! (10분 뒤 재시도)")
        sys.exit(1)
        
    m1 = f"🏆 <b>[1/3] NETFLIX 실시간 랭킹 ({time_str})</b>\n━━━━━━━━━━━━━━━━━━\n\n"
    m1 += format_msg("NETFLIX Global", n_world, limit=10)
    m1 += format_korea_ranking(n_kr)
    m1 += '🔗 <a href="https://flixpatrol.com/top10/netflix/">상세보기</a>\n'
    send_telegram(m1)
    
    d_world = results.get("d_world", {"movies":[], "tv":[]})
    d_kr = results.get("d_kr", {"movies":[], "tv":[]})
    m2 = f"🏆 <b>[2/3] DISNEY+ 실시간 랭킹 ({time_str})</b>\n━━━━━━━━━━━━━━━━━━\n\n"
    m2 += format_msg("DISNEY+", d_world, limit=10)
    m2 += format_korea_ranking(d_kr)
    m2 += '🔗 <a href="https://flixpatrol.com/top10/disney/">상세보기</a>\n'
    send_telegram(m2)
    
    hbo = results.get("hbo", {"movies":[], "tv":[]})
    amz = results.get("amz", {"movies":[], "tv":[]})
    app = results.get("app", {"movies":[], "tv":[]})
    if (hbo['movies'] or hbo['tv'] or amz['movies'] or amz['tv'] or app['movies'] or app['tv']):
        m3 = f"🏆 <b>[3/3] 기타 OTT 통합 랭킹 ({time_str})</b>\n━━━━━━━━━━━━━━━━━━\n\n"
        if hbo['movies'] or hbo['tv']: m3 += format_msg("MAX (HBO)", hbo, limit=5)
        if amz['movies'] or amz['tv']: m3 += format_msg("AMAZON PRIME", amz, limit=5)
        if app['movies'] or app['tv']: m3 += format_msg("APPLE TV+", app, limit=5)
        send_telegram(m3)
        
    print("--- 🏁 수집 및 전송 완료 ---")

if __name__ == "__main__":
    main()

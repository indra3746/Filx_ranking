import os
import sys
import time
import datetime
import requests
from bs4 import BeautifulSoup

# 1. 텔레그램 전송 함수 (HTML 모드로 변경하여 특수문자 에러 방지)
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

# 2. 데이터 수집 함수 (ScraperAPI + 재시도 처리)
def fetch_rankings(platform, loc="world"):
    scraper_api_key = os.environ.get("SCRAPER_API_KEY")
    
    # FlixPatrol 최신 URL 구조 반영 (hbo-max -> max / hbo)
    if platform == "hbo-max":
        p_ids = ["max", "hbo"]
    else:
        p_ids = [platform]
        
    for pid in p_ids:
        target_url = f"https://flixpatrol.com/top10/{pid}/{loc}/"
        print(f"[{platform}] ScraperAPI 접속 시도: {target_url}")
        
        # 💡 일시적 500 에러 대응을 위한 3회 재시도 로직
        for attempt in range(3):
            try:
                payload = {'api_key': scraper_api_key, 'url': target_url}
                res = requests.get('http://api.scraperapi.com', params=payload, timeout=60)
                
                if res.status_code == 200:
                    soup = BeautifulSoup(res.text, 'html.parser')
                    movies = []
                    tv = []

                    # FlixPatrol 실시간 표(Table) 파싱
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
                                        # HTML 이스케이프 기본 처리
                                        title = raw_title.replace("<", "&lt;").replace(">", "&gt;")
                                        if title:
                                            parsed_list.append(f"{rank}위 {title}")
                                    if len(parsed_list) == 10:
                                        break
                        
                        if parsed_list:
                            if idx == 0 and not movies:
                                movies = parsed_list
                            elif idx == 1 and not tv:
                                tv = parsed_list

                    if movies or tv:
                        return {"movies": movies, "tv": tv}
                    break # 성공했으나 데이터가 없는 경우 루프 탈출
                
                elif res.status_code == 500:
                    print(f"⚠️ {pid} 서버 일시 장애(500). ({attempt+1}/3 재시도 중...)")
                    time.sleep(3) # 3초 대기 후 재시도
                elif res.status_code == 404:
                    print(f"⚠️ {pid} 페이지 없음(404)")
                    break
                else:
                    print(f"⚠️ {pid} 응답 에러 (코드: {res.status_code})")
                    break

            except Exception as e:
                print(f"⚠️ 에러 ({pid}): {e}")
                time.sleep(2)
            
    return {"movies": [], "tv": []}

# 3. 메시지 포맷팅 (HTML 태그 적용)
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

# 4. 한국 랭킹 포맷팅 함수 (HTML 태그 적용)
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

# 5. 메인 로직
def main():
    now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9)
    time_str = now.strftime("%y.%m.%d %H:%M")
    
    print(f"--- 실행 ({time_str}) ---")
    
    # [1] NETFLIX
    n_world = fetch_rankings("netflix", "world")
    n_kr = fetch_rankings("netflix", "south-korea")
    
    # 핵심 데이터 수집 실패 시 🚨 깃허브 액션 재시도 유도 (10분 뒤 자동 재실행)
    if not n_world['movies'] and not n_world['tv']:
        print("❌ NETFLIX 데이터 수집 실패! (깃허브 액션 10분 뒤 재시도 실행)")
        sys.exit(1)
    
    m1 = f"🏆 <b>[1/3] NETFLIX 실시간 랭킹 ({time_str})</b>\n━━━━━━━━━━━━━━━━━━\n\n"
    m1 += format_msg("NETFLIX Global", n_world, limit=10)
    m1 += format_korea_ranking(n_kr)
    m1 += '🔗 <a href="https://flixpatrol.com/top10/netflix/">상세보기</a>\n'
    
    send_telegram(m1)
    time.sleep(2)
    
    # [2] DISNEY+
    d_world = fetch_rankings("disney", "world")
    d_kr = fetch_rankings("disney", "south-korea") 
    
    m2 = f"🏆 <b>[2/3] DISNEY+ 실시간 랭킹 ({time_str})</b>\n━━━━━━━━━━━━━━━━━━\n\n"
    m2 += format_msg("DISNEY+", d_world, limit=10)
    m2 += format_korea_ranking(d_kr) 
    m2 += '🔗 <a href="https://flixpatrol.com/top10/disney/">상세보기</a>\n' 
    
    send_telegram(m2)
    time.sleep(2)
    
    # [3] 기타 (MAX, AMAZON, APPLE)
    hbo = fetch_rankings("hbo-max", "world")
    amz = fetch_rankings("amazon-prime", "world")
    app = fetch_rankings("apple-tv", "world")
    
    # 하나라도 데이터가 있는 경우에만 3번 메세지 발송
    if (hbo['movies'] or hbo['tv'] or amz['movies'] or amz['tv'] or app['movies'] or app['tv']):
        m3 = f"🏆 <b>[3/3] 기타 OTT 통합 랭킹 ({time_str})</b>\n━━━━━━━━━━━━━━━━━━\n\n"
        
        if hbo['movies'] or hbo['tv']: 
            m3 += format_msg("MAX (HBO)", hbo, limit=5)
        if amz['movies'] or amz['tv']: 
            m3 += format_msg("AMAZON PRIME", amz, limit=5)
        if app['movies'] or app['tv']:
            m3 += format_msg("APPLE TV+", app, limit=5)
            
        send_telegram(m3)
    
    print("--- 완료 ---")

if __name__ == "__main__":
    main()

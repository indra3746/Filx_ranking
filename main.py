import cloudscraper # 🚨 requests 대신 이걸 씁니다!
from bs4 import BeautifulSoup
import datetime
import os
import time

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
            # 텔레그램 API 전송은 기존 방패(Cloudflare)랑 상관없으므로 특수 툴(scraper)을 쓰되 기본 로직 유지
            scraper = cloudscraper.create_scraper()
            scraper.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown", "disable_web_page_preview": True})
        except Exception as e:
            print(f"전송 실패: {e}")

# 3. 데이터 수집 함수
def fetch_rankings(platform, loc="world"):
    if platform == "hbo-max":
        p_ids = ["hbo", "max", "hbo-max"]
    else:
        p_ids = [platform]
        
    # 🚨 Cloudflare 우회 전용 스크래퍼 생성!
    scraper = cloudscraper.create_scraper()
    
    for pid in p_ids:
        url = f"https://flixpatrol.com/top10/{pid}/{loc}/"
        print(f"[{platform}] 접속 시도: {url}")
        
        try:
            # 🚨 requests.get 대신 scraper.get 사용!
            res = scraper.get(url, timeout=20)
            if res.status_code != 200:
                print(f"⚠️ {pid} 경로 응답 없음 ({res.status_code})")
                continue
            
            soup = BeautifulSoup(res.text, 'html.parser')
            
            movies = []
            tv = []
            
            for header in soup.find_all(['h1', 'h2', 'h3', 'h4']):
                header_text = header.get_text(strip=True).lower()
                
                is_movie = 'movie' in header_text
                is_tv = 'tv' in header_text
                
                if not (is_movie or is_tv):
                    continue
                    
                table = header.find_next('table')
                if not table:
                    continue
                    
                current_list = []
                for row in table.find_all('tr'):
                    cols = row.find_all('td')
                    if len(cols) >= 2:
                        rank_txt = cols[0].get_text(strip=True).replace(".", "")
                        if rank_txt.isdigit():
                            rank = int(rank_txt)
                            
                            link = row.find('a')
                            title_txt = "-"
                            if link:
                                href_parts = [p for p in link.get('href', '').split('/') if p]
                                slug = href_parts[-1] if href_parts else ""
                                raw = link.get_text(strip=True) or link.get('title') or slug.replace('-', ' ').title()
                                title_txt = KOR_MAP.get(slug, raw)
                            else:
                                title_txt = cols[1].get_text(strip=True)

                        current_list.append(f"{rank}위 {title_txt}")
                        
                        if len(current_list) == 10:
                            break
                            
                if is_movie and not movies:
                    movies = current_list
                elif is_tv and not tv:
                    tv = current_list
                    
            if movies or tv:
                return {"movies": movies, "tv": tv}
                
            # [안전장치]
            all_rows = soup.find_all('tr')
            current_list = []
            list_count = 0 
            for row in all_rows:
                cols = row.find_all('td')
                if len(cols) >= 2:
                    rank_txt = cols[0].get_text(strip=True).replace(".", "")
                    if rank_txt.isdigit():
                        rank = int(rank_txt)
                        
                        if rank == 1 and current_list:
                            if list_count == 0: movies = current_list[:]
                            elif list_count == 1: tv = current_list[:]
                            current_list = []
                            list_count += 1
                        
                        link = row.find('a')
                        title_txt = "-"
                        if link:
                            try:
                                slug = link.get('href', '').split('/')[-2]
                            except:
                                slug = ""
                            raw = link.get_text(strip=True) or link.get('title') or slug.replace('-', ' ').title()
                            title_txt = KOR_MAP.get(slug, raw)
                        else:
                            title_txt = cols[1].get_text(strip=True)

                        current_list.append(f"{rank}위 {title_txt}")

            if current_list:
                if list_count == 0: movies = current_list
                elif list_count == 1: tv = current_list
                
            if movies or tv:
                return {"movies": movies, "tv": tv}

        except Exception as e:
            print(f"⚠️ 에러 ({pid}): {e}")
            
    return {"movies": [], "tv": []}

# 4. 메시지 포맷팅
def format_msg(name, data, limit=10):
    msg = f"🎬 **{name}**\n"
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

# 5. 한국 랭킹 포맷팅 함수
def format_korea_ranking(data):
    msg = ""
    if data['movies'] or data['tv']:
        msg += " 🇰🇷 **한국 TOP 10**\n"
        
        if data['movies']:
            msg += " 🎞️ **영화**\n"
            msg += "\n".join([f" {x}" for x in data['movies'][:10]]) + "\n\n" 
            
        if data['tv']:
            msg += " 📺 **TV 쇼**\n"
            msg += "\n".join([f" {x}" for x in data['tv'][:10]]) + "\n\n" 
    return msg

# 6. 메인 로직
def main():
    now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9)
    time_str = now.strftime("%y.%m.%d %H:%M")
    
    print(f"--- 실행 ({time_str}) ---")
    
    # [1] NETFLIX
    n_world = fetch_rankings("netflix", "world")
    n_kr = fetch_rankings("netflix", "south-korea")
    
    m1 = f"🏆 **[1/3] NETFLIX 실시간 랭킹 ({time_str})**\n━━━━━━━━━━━━━━━━━━\n\n"
    m1 += format_msg("NETFLIX Global", n_world, limit=10)
    m1 += format_korea_ranking(n_kr)
    m1 += "🔗 [상세보기](https://flixpatrol.com/top10/netflix/)\n"
    
    send_telegram(m1)
    time.sleep(3)
    
    # [2] DISNEY+
    d_world = fetch_rankings("disney", "world")
    d_kr = fetch_rankings("disney", "south-korea") 
    
    m2 = f"🏆 **[2/3] DISNEY+ 실시간 랭킹 ({time_str})**\n━━━━━━━━━━━━━━━━━━\n\n"
    m2 += format_msg("DISNEY+", d_world, limit=10)
    m2 += format_korea_ranking(d_kr) 
    m2 += "🔗 [상세보기](

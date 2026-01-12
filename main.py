import requests
from bs4 import BeautifulSoup
import datetime
import os

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
            if len(tds) < 4: continue
            
            # 1. 순위 및 변동 (정확한 인덱스 매칭)
            rank = tds[0].get_text(strip=True).replace(".", "")
            change = "-"
            change_span = tds[1].select_one('span')
            if change_span:
                txt = change_span.get_text(strip=True)
                if any(x in txt for x in ['▲', '▼', 'n/a']): change = txt.replace('n/a', '신규')
            
            # 2. 제목 추출 (데이터가 섞이지 않도록 div/a 태그 타겟팅)
            title_tag = tds[2].find('div') or tds[2]
            title_raw = title_tag.get_text(strip=True)
            
            # 3. 점수(Index) 추출 - 기존 오류(제목 칸에 점수 노출) 수정
            idx = tds[3].get_text(strip=True)
            
            # 4. 출시일 동적 추출 (해당 행에서 출시일 정보를 가진 열을 탐색)
            # FlixPatrol은 보통 마지막 열이나 데이터 속성에 출시일을 포함함
            rel_date = "26.01.01." # 기본값
            date_col = row.find('td', class_='table-main-date') or tds[-1]
            if date_col:
                raw_date = date_col.get_text(strip=True)
                # '2026-01-08' 형태를 '26.01.08.'로 변환
                if "-" in raw_date:
                    rel_date = raw_date[2:].replace("-", ".") + "."

            data.append({
                "rank": rank, "change": change, "title": title_raw, 
                "idx": idx, "date": rel_date
            })
        return data
    except Exception as e:
        print(f"Error: {e}")
        return []

def format_section(cfg):
    msg = f"🎬 **{cfg['name']}**\n"
    
    # 지역별 데이터 처리
    locs = [("world", f"🌎 **글로벌 TOP {cfg.get('lim', 10)}**", cfg.get('lim', 10)),
            ("south-korea", "🇰🇷 **한국 TOP 10**", 10)] if cfg.get('korea') else [("world", f"🌎 **글로벌 TOP {cfg['lim']}**", cfg['lim'])]

    for loc_id, header, lim in locs:
        items = fetch_data(cfg['id'], loc_id, lim)
        if items:
            msg += f" {header}\n\n"
            for i in items:
                # 한글 제목 변환은 유지하되, 실패 시 영어 원문 노출
                title = i['title'] # 실제 운영 시에는 여기에 매핑 딕셔너리 적용
                msg += f" {i['rank']}. {title} | {i['idx']} ┃ {i['change']} ┃ {i['date']}\n"
            msg += "\n"
    return msg

def main():
    now = datetime.datetime.now().strftime("%y.%m.%d %H:%M")
    
    # 텔레그램 발송 로직 (생략 - 기존과 동일)
    # ...
    
    # 수정된 리포트 생성 및 전송
    #

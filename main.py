import os
import requests
from datetime import datetime
import pytz
import yfinance as yf

# --- [자산 데이터: 사진 기반 최종 정밀 업데이트] ---

# 1. 종합계좌 - 해외주식 (소수점 합산)
OVERSEAS_COMP = [
    {"name": "테슬라", "tk": "TSLA", "qty": 31.809023, "inv": 17405897},
    {"name": "BITX(비트코인2x)", "tk": "BITX", "qty": 187.943492, "inv": 17000000},
    {"name": "엔비디아", "tk": "NVDA", "qty": 4.028363, "inv": 1000000},
    {"name": "팔란티어", "tk": "PLTR", "qty": 4.234369, "inv": 1000000},
    {"name": "인베스코 QQQ", "tk": "QQQ", "qty": 4.400101, "inv": 3800000},
    {"name": "GE베르노바", "tk": "GEV", "qty": 2.381195, "inv": 2000000},
    {"name": "MP머티리얼스", "tk": "MP", "qty": 12.816002, "inv": 1500000},
    {"name": "오클로", "tk": "OKLO", "qty": 1.832425, "inv": 300000},
    {"name": "뉴스케일파워(SMR)", "tk": "SMR", "qty": 24.737559, "inv": 1800000},
    {"name": "니오코프", "tk": "NB", "qty": 102, "inv": 1500000},
    {"name": "USA레어어스", "tk": "USAR", "qty": 20, "inv": 1238032}
]

# 2. 종합계좌 - 국내주식
DOMESTIC_COMP = [
    {"name": "한화에어로", "tk": "012450", "qty": 20, "inv": 17997000},
    {"name": "하이닉스(소)", "tk": "000660", "qty": 0.727501, "inv": 419979},
    {"name": "카카오", "tk": "035720", "qty": 1, "inv": 66800},
    {"name": "NEW", "tk": "160550", "qty": 1, "inv": 10400},
    {"name": "종합계좌 예수금", "tk": "CASH", "qty": 8107, "inv": 8107}
]

# 3. 연금저축 - 국내주식
PENSION_SAVING = [
    {"name": "KODEX 미국S&P500", "tk": "379780", "qty": 808, "inv": 17307325}
]

# 4. 퇴직연금(DC) - 종목별 매입금 및 수량 정밀 수정
RETIRE_DC = [
    {"name": "KODEX 미국반도체", "tk": "446770", "qty": 141, "inv": 4973775},
    {"name": "TIGER 반도체TOP10", "tk": "396500", "qty": 269, "inv": 4998020},
    {"name": "KODEX 미국서학개미", "tk": "480310", "qty": 345, "inv": 8552550},
    {"name": "TIGER 미국AI전력SMR", "tk": "483170", "qty": 768, "inv": 5689920},
    {"name": "KODEX 미국S&P500", "tk": "379780", "qty": 219, "inv": 4997580},
    {"name": "미래에셋 TDF 2050", "tk": "CASH", "qty": 12426930, "inv": 12446360}, #
    {"name": "미래에셋 현금성자산", "tk": "CASH", "qty": 765214, "inv": 765214}   #
]

def get_real_price(ticker):
    if ticker == "CASH": return 1.0
    try:
        # 네이버 금융에서 실시간 종가 추출 (BS4 사용)
        url = f"https://finance.naver.com/item/main.naver?code={ticker}"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(res.text, 'html.parser')
        # 종가 위치: no_today 클래스 안의 blind 스팬
        price_tag = soup.select_one(".no_today .blind")
        return float(price_tag.text.replace(',', ''))
    except: return None

def get_report():
    try:
        curr_rate = yf.Ticker("USDKRW=X").history(period="1d")['Close'].iloc[-1]
    except: curr_rate = 1442.0

    now = datetime.now(pytz.timezone('Asia/Seoul')).strftime('%y.%m.%d %H:%M')
    total_inv_all, total_eval_all = 0, 0

    def process_section(title, assets, is_os=False):
        nonlocal total_inv_all, total_eval_all
        sub_inv, sub_eval = 0, 0
        item_txt = ""
        
        for s in assets:
            if s['tk'] == "CASH": price = 1.0
            elif is_os:
                try: 
                    hist = yf.Ticker(s['tk']).history(period="1d")
                    price = hist['Close'].iloc[-1]
                except: price = s['inv'] / (s['qty'] * curr_rate)
            else:
                price = get_real_price(s['tk'])
                if price is None: price = s['inv'] / s['qty']
            
            curr_price_krw = price * (curr_rate if is_os else 1)
            avg_price_krw = s['inv'] / s['qty']
            eval_krw = curr_price_krw * s['qty']
            profit = eval_krw - s['inv']
            roi = (profit / s['inv'] * 100)
            
            emoji = '🔴' if profit >= 0 else '🔵'
            qty_label = f" ({s['qty']:g}주)" if s['tk'] != "CASH" else ""
            
            item_txt += f"{emoji} {s['name']}{qty_label}\n"
            item_txt += f"평가금액: {eval_krw:,.0f}원\n"
            item_txt += f"수익금: {profit:+,.0f}원\n"
            item_txt += f"수익률: {roi:+.2f}%\n"
            item_txt += f"현재가: {curr_price_krw:,.0f}원\n"
            item_txt += f"평단가: {avg_price_krw:,.0f}원\n\n"
            
            sub_inv += s['inv']; sub_eval += eval_krw
        
        sub_profit = sub_eval - sub_inv
        sub_roi = (sub_profit / sub_inv * 100)
        
        header = f"\n━━━━━━━━━━━━━━━━━━\n📦 {title}\n"
        header += f"계좌총액: {sub_eval:,.0f}원\n"
        header += f"수익금: {sub_profit:+,.0f}원\n"
        header += f"수익률: {sub_roi:+.2f}%\n"
        
        total_inv_all += sub_inv; total_eval_all += sub_eval
        return header + item_txt

    final_header = f"📈 통합 자산 실시간 리포트 ({now})\n"
    sections = [
        process_section("종합계좌 (해외)", OVERSEAS_COMP, True),
        process_section("종합계좌 (국내)", DOMESTIC_COMP),
        process_section("연금저축 (국내)", PENSION_SAVING),
        process_section("퇴직연금 (DC)", RETIRE_DC)
    ]
    
    total_profit = total_eval_all - total_inv_all
    total_roi = (total_profit / total_inv_all * 100)
    final_header += f"총액: {total_eval_all:,.0f}원({total_profit:+,.0f}원 / {total_roi:+.2f}%)\n"
    
    return final_header + "".join(sections)

def send_msg(text):
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('CHAT_ID')
    if token and chat_id:
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", 
                     json={"chat_id": chat_id, "text": text})

if __name__ == "__main__":
    send_msg(get_report())

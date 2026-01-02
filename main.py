import os
import requests
from datetime import datetime
import pytz
import yfinance as yf
import FinanceDataReader as fdr

# --- [1. 종합계좌 - 해외주식] (소수점 정밀 합산) ---
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

# --- [2. 종합계좌 - 국내주식] ---
DOMESTIC_COMP = [
    {"name": "한화에어로", "tk": "012450", "qty": 20, "inv": 17997000},
    {"name": "하이닉스(소)", "tk": "000660", "qty": 0.727501, "inv": 419979},
    {"name": "카카오", "tk": "035720", "qty": 1, "inv": 66800},
    {"name": "NEW", "tk": "160550", "qty": 1, "inv": 10400}
]

# --- [3. 연금저축 - 국내주식] ---
PENSION_INVEST = [
    {"name": "KODEX 미국S&P500", "tk": "379780", "qty": 808, "inv": 17307325}
]

# --- [4. 퇴직연금(DC)] ---
RETIRE_PENSION = [
    {"name": "TIGER 미국AI전력SMR", "tk": "483170", "qty": 672, "inv": 4999680},
    {"name": "DC 현금성 자산", "tk": "CASH", "qty": 36654204, "inv": 36654204} # qty를 금액으로 설정
]

def get_price(ticker, is_os=False):
    if ticker == "CASH": return 1.0
    try:
        if is_os:
            data = yf.Ticker(ticker).history(period="1d")
            return data['Close'].iloc[-1] if not data.empty else None
        else:
            # fdr 우선, 실패 시 yf fallback
            df = fdr.DataReader(ticker)
            if not df.empty: return float(df['Close'].iloc[-1])
            data = yf.Ticker(f"{ticker}.KS").history(period="1d")
            return data['Close'].iloc[-1] if not data.empty else None
    except: return None

def get_report():
    try:
        curr_rate = yf.Ticker("USDKRW=X").history(period="1d")['Close'].iloc[-1]
    except: curr_rate = 1442.0

    now = datetime.now(pytz.timezone('Asia/Seoul')).strftime('%y.%m.%d %H:%M')
    report = f"📈 통합 자산 실시간 리포트 ({now})\n환율: {curr_rate:,.2f}원\n"
    total_inv, total_eval = 0, 0

    def process_section(title, assets, is_os=False):
        nonlocal total_inv, total_eval
        sub_inv, sub_eval = 0, 0
        txt = f"\n━━━━━━━━━━━━━━━━━━\n📦 {title}\n"
        
        for s in assets:
            price = get_price(s['tk'], is_os)
            if price is None:
                # 가격 로딩 실패 시 원금으로 유지하여 총액 방어
                price = s['inv'] / s['qty']
                txt += f"⚠️ {s['name']}: 가격 로딩 지연(원가계산)\n"
            
            eval_krw = price * s['qty'] * (curr_rate if is_os else 1)
            profit = eval_krw - s['inv']
            roi = (profit / s['inv'] * 100)
            
            txt += f"{'🔴' if profit >= 0 else '🔵'} {s['name']}: {roi:+.2f}% ({eval_krw:,.0f}원)\n"
            sub_inv += s['inv']; sub_eval += eval_krw
        
        total_inv += sub_inv; total_eval += sub_eval
        return txt

    report += process_section("종합계좌 (해외)", OVERSEAS_COMP, True)
    report += process_section("종합계좌 (국내)", DOMESTIC_COMP)
    report += process_section("연금저축 (국내)", PENSION_INVEST)
    report += process_section("퇴직연금 (DC)", RETIRE_PENSION)

    report += f"\n━━━━━━━━━━━━━━━━━━\n💰 통합 총 자산: {total_eval:,.0f}원"
    report += f"\n📊 통합 총 손익: {total_eval-total_inv:+,.0f}원 ({(total_eval-total_inv)/total_inv*100:+.2f}%)"
    return report

def send_msg(text):
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('CHAT_ID')
    if token and chat_id:
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", 
                     json={"chat_id": chat_id, "text": text})

if __name__ == "__main__":
    send_msg(get_report())

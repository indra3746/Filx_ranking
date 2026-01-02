import os
import requests
import time
from datetime import datetime
import pytz
import yfinance as yf

# --- [사용자 포트폴리오 데이터 - 환차 정밀 보정] ---
# fx_base: 제공해주신 환차손익잔고 사진을 기반으로 역산한 매수 시점 환율입니다.
OVERSEAS = [
    {"name": "테슬라(일)", "tk": "TSLA", "qty": 30.0, "avg": 380.3712, "inv": 16373841, "fx_base": 1417.8}, #
    {"name": "테슬라(소)", "tk": "TSLA", "qty": 1.809023, "avg": 397.5919, "inv": 1032056, "fx_base": 1416.5}, #
    {"name": "BITX(일)", "tk": "BITX", "qty": 186.0, "avg": 60.1199, "inv": 16045475, "fx_base": 1420.3}, #
    {"name": "NVDA(일)", "tk": "NVDA", "qty": 2.0, "avg": 175.9806, "inv": 505029, "fx_base": 1389.2}, #
    {"name": "QQQ(일)", "tk": "QQQ", "qty": 3.0, "avg": 600.39, "inv": 2584499, "fx_base": 1395.2}, #
    {"name": "PLTR(일)", "tk": "PLTR", "qty": 2.0, "avg": 163.8334, "inv": 470169, "fx_base": 1389.0}, #
    {"name": "SMR(일)", "tk": "SMR", "qty": 17.0, "avg": 42.4718, "inv": 1036026, "fx_base": 1402.5}, #
    {"name": "USAR(일)", "tk": "USAR", "qty": 20.0, "avg": 43.14, "inv": 1238032, "fx_base": 1422.0} #
]

DOMESTIC_PENSION = [
    {"name": "한화에어로", "tk": "012450.KS", "qty": 20.0, "inv": 17997000}, #
    {"name": "하이닉스(소)", "tk": "000660.KS", "qty": 0.727501, "inv": 419979}, #
    {"name": "KODEX S&P(연금)", "tk": "379780.KS", "qty": 808.0, "inv": 17307325}, #
    {"name": "TIGER 반도체", "tk": "396500.KS", "qty": 269.0, "inv": 4998020}, #
    {"name": "미국AI전력SMR", "tk": "483170.KS", "qty": 672.0, "inv": 4999680} #
]

def get_report():
    # 실시간 환율 및 KST 시간 설정
    rate_info = yf.Ticker("USDKRW=X").history(period="1d")
    curr_rate = rate_info['Close'].iloc[-1]
    now = datetime.now(pytz.timezone('Asia/Seoul')).strftime('%y.%m.%d %H:%M')
    
    report = f"📈 주식 수익률 통합 리포트 ({now})\n환율: {curr_rate:,.2f}원\n━━━━━━━━━━━━━━━━━━\n"
    total_inv, total_eval = 0, 0

    def process_assets(title, asset_list, is_os=False):
        nonlocal total_inv, total_eval
        sub_inv, sub_eval = 0, 0
        txt = f"\n📂 {title}\n"
        
        for s in asset_list:
            try:
                ticker = yf.Ticker(s['tk'])
                price = ticker.history(period="1d")['Close'].iloc[-1]
                
                if is_os:
                    eval_krw = price * s['qty'] * curr_rate
                    # 환차익(원) = 현재외화가치 * (현재환율 - 매수환율)
                    fx_gain_krw = (price * s['qty']) * (curr_rate - s['fx_base'])
                    profit_krw = eval_krw - s['inv']
                    roi = profit_krw / s['inv'] * 100
                    status = f"{roi:+.2f}% (환차:{fx_gain_krw:+,.0f}원)"
                else:
                    eval_krw = price * s['qty']
                    profit_krw = eval_krw - s['inv']
                    roi = profit_krw / s['inv'] * 100
                    status = f"{roi:+.2f}%"

                emoji = "🔴" if profit_krw >= 0 else "🔵"
                txt += f"{emoji} {s['name']}: {status}\n"
                txt += f"   현재: {eval_krw:,.0f}원 ({profit_krw:+,.0f}원)\n"
                
                sub_inv += s['inv']
                sub_eval += eval_krw
            except: txt += f"⚠️ {s['name']} 로딩 실패\n"

        sub_roi = (sub_eval - sub_inv) / sub_inv * 100
        sub_emoji = "🔺" if sub_roi >= 0 else "🔻"
        txt += f"▶ 요약: {sub_emoji} {sub_roi:+.2f}% ({sub_eval-sub_inv:+,.0f}원)\n"
        total_inv += sub_inv
        total_eval += sub_eval
        return txt

    report += process_assets("해외 주식 계좌", OVERSEAS, True)
    report += process_assets("국내 및 연금 계좌", DOMESTIC_PENSION)
    
    total_roi = (total_eval - total_inv) / total_inv * 100
    total_emoji = "🔥" if total_roi >= 0 else "❄️"
    report += "\n━━━━━━━━━━━━━━━━━━\n"
    report += f"{total_emoji} 통합 총 자산: {total_eval:,.0f}원\n"
    report += f"💰 통합 총 손익: {total_eval-total_inv:+,.0f}원 ({total_roi:+.2f}%)\n"
    return report

def send_msg(text):
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('CHAT_ID')
    requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={"chat_id": chat_id, "text": text})

if __name__ == "__main__":
    send_msg(get_report())

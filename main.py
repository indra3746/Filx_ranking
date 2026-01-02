import os
import requests
import time
from datetime import datetime
import pytz
import yfinance as yf
import FinanceDataReader as fdr

# --- [사용자 데이터] ---
OVERSEAS = [
    {"name": "테슬라(일)", "tk": "TSLA", "qty": 30.0, "avg": 380.3712, "inv": 16373841, "fx_base": 1417.8},
    {"name": "테슬라(소)", "tk": "TSLA", "qty": 1.809023, "avg": 397.5919, "inv": 1032056, "fx_base": 1416.5},
    {"name": "BITX(일)", "tk": "BITX", "qty": 186.0, "avg": 60.1199, "inv": 16045475, "fx_base": 1420.3},
    {"name": "NVDA(일)", "tk": "NVDA", "qty": 2.0, "avg": 175.9806, "inv": 505029, "fx_base": 1389.2},
    {"name": "QQQ(일)", "tk": "QQQ", "qty": 3.0, "avg": 600.39, "inv": 2584499, "fx_base": 1395.2},
    {"name": "PLTR(일)", "tk": "PLTR", "qty": 2.0, "avg": 163.8334, "inv": 470169, "fx_base": 1389.0},
    {"name": "SMR(일)", "tk": "SMR", "qty": 17.0, "avg": 42.4718, "inv": 1036026, "fx_base": 1402.5},
    {"name": "USAR(일)", "tk": "USAR", "qty": 20.0, "avg": 43.14, "inv": 1238032, "fx_base": 1422.0}
]

DOMESTIC_PENSION = [
    {"name": "한화에어로", "tk": "012450", "qty": 20.0, "inv": 17997000},
    {"name": "하이닉스(소)", "tk": "000660", "qty": 0.727501, "inv": 419979},
    {"name": "KODEX S&P(연금)", "tk": "379780", "qty": 808.0, "inv": 17307325},
    {"name": "TIGER 반도체", "tk": "396500", "qty": 269.0, "inv": 4998020},
    {"name": "미국AI전력SMR", "tk": "483170", "qty": 672.0, "inv": 4999680} # TIGER 미국AI전력핵심인프라
]

def get_report():
    try:
        rate_info = yf.Ticker("USDKRW=X").history(period="1d")
        curr_rate = rate_info['Close'].iloc[-1]
    except:
        curr_rate = 1400.0

    now = datetime.now(pytz.timezone('Asia/Seoul')).strftime('%y.%m.%d %H:%M')
    report = f"📈 주식 수익률 통합 리포트 ({now})\n환율: {curr_rate:,.2f}원\n━━━━━━━━━━━━━━━━━━\n"
    total_inv, total_eval = 0, 0

    def process_assets(title, asset_list, is_os=False):
        nonlocal total_inv, total_eval
        sub_inv, sub_eval = 0, 0
        txt = f"\n📂 {title}\n"
        
        for s in asset_list:
            try:
                if is_os:
                    price = yf.Ticker(s['tk']).history(period="1d")['Close'].iloc[-1]
                else:
                    # 국내 주식: FinanceDataReader 시도, 실패 시 yfinance(.KS) 시도
                    try:
                        df = fdr.DataReader(s['tk'])
                        price = float(df['Close'].iloc[-1])
                    except:
                        price = yf.Ticker(f"{s['tk']}.KS").history(period="1d")['Close'].iloc[-1]

                eval_krw = price * s['qty']
                if is_os:
                    eval_krw *= curr_rate
                    fx_gain = (price * s['qty']) * (curr_rate - s['fx_base'])
                    profit = eval_krw - s['inv']
                    status = f"{(profit/s['inv']*100):+.2f}% (환차:{fx_gain:+,.0f}원)"
                else:
                    profit = eval_krw - s['inv']
                    status = f"{(profit/s['inv']*100):+.2f}%"

                txt += f"{'🔴' if profit >= 0 else '🔵'} {s['name']}: {status}\n"
                txt += f"    현재: {eval_krw:,.0f}원 ({profit:+,.0f}원)\n"
                sub_inv += s['inv']; sub_eval += eval_krw
            except:
                txt += f"⚠️ {s['name']} 로딩 실패\n"

        if sub_inv > 0:
            roi = (sub_eval-sub_inv)/sub_inv*100
            txt += f"▶ 요약: {'🔺' if roi>=0 else '🔻'} {roi:+.2f}% ({sub_eval-sub_inv:+,.0f}원)\n"
            total_inv += sub_inv; total_eval += sub_eval
        return txt

    report += process_assets("해외 주식 계좌", OVERSEAS, True)
    report += process_assets("국내 및 연금 계좌", DOMESTIC_PENSION)
    
    if total_inv > 0:
        total_roi = (total_eval-total_inv)/total_inv*100
        report += "\n━━━━━━━━━━━━━━━━━━\n"
        report += f"💰 통합 총 자산: {total_eval:,.0f}원\n"
        report += f"📊 통합 총 손익: {total_eval-total_inv:+,.0f}원 ({total_roi:+.2f}%)\n"
    return report

def send_msg(text):
    print("--- [생성된 리포트 내용] ---")
    print(text) # GitHub 로그에서 내용을 볼 수 있게 출력
    
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('CHAT_ID')
    
    if not token or not chat_id:
        print("❌ 에러: TELEGRAM_TOKEN 또는 CHAT_ID 환경변수가 설정되지 않았습니다.")
        return

    res = requests.post(f"https://api.telegram.org/bot{token}/sendMessage", 
                         json={"chat_id": chat_id, "text": text})
    
    if res.status_code == 200:
        print("✅ 텔레그램 메시지 전송 성공!")
    else:
        print(f"❌ 텔레그램 전송 실패: {res.status_code}")
        print(res.text)

if __name__ == "__main__":
    send_msg(get_report())

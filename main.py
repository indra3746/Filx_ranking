import os
import requests
import time
from datetime import datetime
import pytz
import yfinance as yf

# --- [사용자 포트폴리오 데이터 세팅] ---
# 해외 주식: 명칭, 티커, 수량, 달러평단, 원화매입금, 매수기준환율(역산값)
# fx_base는 제공해주신 IMG_9906~9908의 환차손익 데이터를 바탕으로 설정되었습니다.
OVERSEAS = [
    {"name": "테슬라(일)", "tk": "TSLA", "qty": 30.0, "avg": 380.3712, "inv": 16373841, "fx_base": 1417.8}, #
    {"name": "테슬라(소)", "tk": "TSLA", "qty": 1.809023, "avg": 397.5919, "inv": 1032056, "fx_base": 1416.5}, #
    {"name": "BITX(일)", "tk": "BITX", "qty": 186.0, "avg": 60.1199, "inv": 16045475, "fx_base": 1420.3}, #
    {"name": "BITX(소)", "tk": "BITX", "qty": 1.943492, "avg": 56.9979, "inv": 158951, "fx_base": 1420.0}, #
    {"name": "NVDA(일)", "tk": "NVDA", "qty": 2.0, "avg": 175.9806, "inv": 505029, "fx_base": 1389.2}, #
    {"name": "NVDA(소)", "tk": "NVDA", "qty": 2.028363, "avg": 187.7459, "inv": 546434, "fx_base": 1415.0}, #
    {"name": "PLTR(일)", "tk": "PLTR", "qty": 2.0, "avg": 163.8334, "inv": 470169, "fx_base": 1389.0}, #
    {"

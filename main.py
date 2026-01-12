name: OTT Ranking Bot

on:
  schedule:
    # UTC 기준 (KST 08:00, 15:00, 20:00)
    - cron: '0 23 * * *'  # 한국 오전 8시
    - cron: '0 6 * * *'   # 한국 오후 3시
    - cron: '0 11 * * *'  # 한국 오후 8시
  workflow_dispatch: # 수동 실행 버튼 활성화

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'

      - name: Install dependencies
        run: |
          pip install requests beautifulsoup4

      - name: Run Bot
        env:
          TELEGRAM_TOKEN: ${{ secrets.TELEGRAM_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
        run: python main.py

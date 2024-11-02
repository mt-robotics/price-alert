import os
from dotenv import load_dotenv, dotenv_values

load_dotenv()

def check_env_vars():
    env_vars = dotenv_values()

    for key, val in env_vars.items():
        if not val:
            raise Exception(f"Missing required environment variable: {key}")
        print(f"Loaded environment variable: {key}")


# Shared state (this will be injected into classes)
shared_state = {
    'last_price': None,
    'alert_sent_recently': False
}

# Telegram bot settings
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
ERROR_REPORT_BOT_TOKEN = os.getenv("ERROR_REPORT_BOT_TOKEN", "")
ERROR_REPORT_CHAT_ID = os.getenv("ERROR_REPORT_CHAT_ID", "")

# Google Sheets settings
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "")
GOOGLE_WORKSHEET_NAME = os.getenv("GOOGLE_WORKSHEET_NAME", "") 

# Trading pair and price change value
TICKER = 'BTC/USDC'
# PRICE_CHANGE_THRESHOLD = 5
PRICE_CHANGE_PERCENTAGE = 0.001

# Sleep time (in seconds)
SLEEP_TIME = 30

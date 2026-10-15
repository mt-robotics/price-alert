import os
from dotenv import load_dotenv, dotenv_values

load_dotenv()


def check_env_vars():
    env_vars = dotenv_values()

    for key, val in env_vars.items():
        if not val:
            raise ValueError(f"Missing required environment variable: {key}")
        print(f"Loaded environment variable: {key}")


# Shared state (this will be injected into classes)
shared_state = {"last_price": None, "alert_sent_recently": False}

# Telegram bot settings
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
ERROR_REPORT_BOT_TOKEN = os.getenv("ERROR_REPORT_BOT_TOKEN", "")
ERROR_REPORT_CHAT_ID = os.getenv("ERROR_REPORT_CHAT_ID", "")

# Google Sheets settings
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "")
GOOGLE_WORKSHEET_NAME = os.getenv("GOOGLE_WORKSHEET_NAME", "")

# Trading pair and price change value
# TICKER = "BTC/USDC"
TICKER = "btcusdc"
# PRICE_CHANGE_THRESHOLD = 5
PRICE_CHANGE_PERCENTAGE = 0.001
ROUNDED_PRICE_CHANGE = 1000

# Sleep time (in seconds)
SLEEP_TIME = 30

# More Telegram settings
LAST_TELEGRAM_ALERT_TIME = 0  # Stores the time when the last alert was sent

MAX_RETRIES = 10  # Maximum reconnection attempts
RETRY_COUNT = 0  # RETRY COUNTER

# Number of rows after which to flush data to Google Sheets for Batch Update logic
BATCH_LIMIT = 10

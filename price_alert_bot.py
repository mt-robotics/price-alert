import ccxt
import gspread
import requests
from oauth2client.service_account import ServiceAccountCredentials
import time
from datetime import datetime, timezone

class PriceAlertBot:
    def __init__(self, config):
        # Injected dependencies
        self.config = config  # Inject config module (telegram, sheet, etc.)

        # Binance API setup
        self.binance = ccxt.binanceusdm()

        # Google Sheets setup
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        credentials = ServiceAccountCredentials.from_json_keyfile_name('trading-price-alert-fa51679be1d2.json', scope)
        client = gspread.authorize(credentials=credentials)
        self.sheet = client.open_by_key(self.config.GOOGLE_SHEET_ID).worksheet(config.GOOGLE_WORKSHEET_NAME)

        # Telegram bot setup
        self.telegram_bot_token = self.config.TELEGRAM_BOT_TOKEN
        self.telegram_chat_id = self.config.TELEGRAM_CHAT_ID
        
        # Trading settings
        self.ticker = self.config.TICKER
        # self.price_change_threshold = self.config.PRICE_CHANGE_THRESHOLD
        self.price_change_percentage = self.config.PRICE_CHANGE_PERCENTAGE

    # Method to send a message to Telegram
    def send_telegram_message(self, message):
        url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
        params = {
            "chat_id": self.telegram_chat_id, 
            "text": message, 
            "parse_mode": "HTML"
        }

        requests.post(url, params=params)

    def send_error_report(self, message):
        url = f"https://api.telegram.org/bot{self.config.ERROR_REPORT_BOT_TOKEN}/sendMessage"
        params = {
            "chat_id": self.config.ERROR_REPORT_CHAT_ID, 
            "text": message, 
            "parse_mode": "HTML"
        }

        requests.post(url=url, params=params)

    # Method to check price, log, and alert
    def check_price(self):
        retries = 0
        max_retries = 5

        while retries < max_retries:
            try:
                # Fetch the latest ticker information
                fetch_ticker = self.binance.fetch_ticker(self.ticker)
                current_price = fetch_ticker['last']
                volume = fetch_ticker['quoteVolume']
                current_time_ms = fetch_ticker['timestamp']

                # Convert the timestamp to a human-readable format (yyyy/mm/dd hh:mm:ss)
                current_time = datetime.fromtimestamp(current_time_ms / 1000, tz=timezone.utc).strftime('%Y/%m/%d %H:%M:%S')

                # Access the shared last price from the shared state
                last_price = self.config.shared_state['last_price']

                if last_price:
                    price_change_percentage = abs(current_price - last_price) / last_price

                    # Check if the price change is significant enough to trigger an update
                    if price_change_percentage >= self.price_change_percentage:
                        # Format the prices and volume with thousand separators
                        formatted_last_price = f"{last_price:,.2f}"
                        formatted_current_price = f"{current_price:,.2f}"
                        # Convert the volume from 500,000,000 to 500M
                        formatted_volume = f"{round(volume / 1000000, 2):,.2f}M" if volume >= 1000000 else f"{volume:,.2f}"

                        # Log timestamp, ticker, last_price, new price, price_change, and volume into Google Sheet
                        self.sheet.append_row([
                            current_time,
                            self.ticker,
                            last_price,
                            current_price,
                            price_change_percentage,
                            volume
                        ])

                        # Prepare message for Telegram
                        change_direction = "⬆️increased" if current_price > last_price else "🔻decreased"
                        message = (
                            f"Time: {current_time}\n"
                            f"<b>{self.ticker}</b> Price <b>{change_direction}</b> by\n"
                            f"<b>{(price_change_percentage * 100):,.2f}%</b>\n"                            
                            f"Trading Volume: <u>{formatted_volume}</u>\n\n"
                            f"Previous Price: {formatted_last_price}\n"
                            f"Current Price: <b>{formatted_current_price}</b>"
                        )

                        # Send message via telegram
                        self.send_telegram_message(message)

                # Update the shared last_price with the current price
                self.config.shared_state['last_price'] = current_price

                # Exit retry loop if success
                break

            except ccxt.NetworkError as e:
                self.send_error_report(f"PriceAlertBot - Network error: {e}")
                print(f"Network error: {e}")
            except ccxt.ExchangeError as e:
                self.send_error_report(f"PriceAlertBot- Exchange error: {e}")
                print(f"Exchange error: {e}")
            except ccxt.RateLimitExceeded:
                wait_time = 2 ** retries
                self.send_error_report(f"PriceAlertBot - Rate limit exceeded. Retrying in {wait_time} seconds...")
                print(f"Rate limit exceeded. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                retries += 1
            except Exception as e:
                self.send_error_report(f"PriceAlertBot - Unexpected Error: {e}")
                print(f"Error: {e}")
                retries += 1

import ccxt
import gspread
import requests
from oauth2client.service_account import ServiceAccountCredentials
import time
from datetime import datetime, timezone
import threading

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

    # Method to send a delayed error report
    def send_delayed_error_report(self, error_message):
        def delayed_report():
            # Delay to check if an alert is sent shortly after the error 
            time.sleep(5)  # 5-second delay

            # Check if an alert was sent in the last few seconds
            if not self.config.shared_state.get('alert_sent_recently', False):
                # Send the error message if no alert was sent recently
                self.send_error_report(error_message)

        # Start a separate thread for the delayed error report
        threading.Thread(target=delayed_report).start()

    # Method to check price, log, and alert
    def check_price(self):
        retries = 0
        max_retries = 3

        error_message = None  # Initialize error_message outside the loop
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
                            f"{current_time}\n"
                            f"<b><u>{self.ticker}</u></b> {change_direction} by <b>{(price_change_percentage * 100):,.2f}%</b>\n"
                            f"From {formatted_last_price} To <b><u>{formatted_current_price}</u></b>\n"
                            f"Trading Volume: <u>{formatted_volume}</u>"
                        )

                        # Send message via telegram
                        self.send_telegram_message(message)
                        # Change the alert_sent_recently flag to True
                        self.config.shared_state['alert_sent_recently'] = True

                        # Reset alert status to False after 5 seconds
                        def reset_alert_status():
                            self.config.shared_state['alert_sent_recently'] = False
                        # Start a 5-second timer in a separate thread to reset `alert_sent_recently` to False. This allows the bot's main thread to continue fetching prices and sending alerts without pausing or blocking while waiting to reset the alert flag.
                        threading.Timer(5, reset_alert_status).start()

                # Update the shared last_price with the current price
                self.config.shared_state['last_price'] = current_price

                # Exit retry loop if success
                break

            except ccxt.NetworkError as e:
                error_message = f"PriceAlertBot - Network error: {e}"
                print(error_message)
                retries += 1
                time.sleep(2 ** retries)  # Exponential backoff on retry

            except ccxt.ExchangeError as e:
                error_message = f"PriceAlertBot- Exchange error: {e}"
                print(error_message)
                retries += 1
                time.sleep(2 ** retries)

            except ccxt.RateLimitExceeded:
                wait_time = 2 ** retries
                error_message = f"PriceAlertBot - Rate limit exceeded. Retrying in {wait_time} seconds..."
                print(error_message)
                retries += 1
                time.sleep(wait_time)
                
            except Exception as e:
                error_message = f"PriceAlertBot - Unexpected Error: {e}"
                print(error_message)
                retries += 1
                time.sleep(2 ** retries)

        # After retrying, send delayed error if still unsuccessful
        if retries == max_retries:
            self.send_delayed_error_report(error_message)

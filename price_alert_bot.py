import time
import json
import math
import logging
import asyncio
import websockets
import gspread
import gspread.utils
import requests
from oauth2client.service_account import ServiceAccountCredentials


# logging.basicConfig(level=logging.DEBUG)


class PriceAlertBot:
    def __init__(self, cfg):
        # Injected dependencies
        self.config = cfg  # Inject config module (telegram, sheet, etc.)

        self.last_telegram_alert_time = (
            0  # Stores the time when the last alert was sent
        )

        # # Binance API setup
        # self.binance = ccxt.binanceusdm()

        # Google Sheets setup
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ]
        credentials = ServiceAccountCredentials.from_json_keyfile_name(
            "trading-price-alert-fa51679be1d2.json", scope
        )
        client = gspread.authorize(credentials=credentials)
        self.sheet = client.open_by_key(self.config.GOOGLE_SHEET_ID).worksheet(
            self.config.GOOGLE_WORKSHEET_NAME
        )

        # Data accumulation batch
        self.data_batch = []  # Stores rows to be added to Google Sheets
        self.batch_limit = self.config.BATCH_LIMIT
        self.last_batch_update_time = time.time()  # Timestamp of the last batch update

        # Telegram bot setup
        self.telegram_bot_token = self.config.TELEGRAM_BOT_TOKEN
        self.telegram_chat_id = self.config.TELEGRAM_CHAT_ID

        # Trading settings
        self.ticker = self.config.TICKER
        # self.price_change_threshold = self.config.PRICE_CHANGE_THRESHOLD
        self.price_change_percentage = self.config.PRICE_CHANGE_PERCENTAGE

        self.last_telegram_alert_time = self.config.LAST_TELEGRAM_ALERT_TIME
        self.max_retries = self.config.MAX_RETRIES
        self.retry_count = self.config.RETRY_COUNT

    async def listen_to_binance(self):
        url = f"wss://stream.binance.com:9443/ws/{self.ticker}@ticker"

        # Define a maximum number of reties or an infinite loop
        while True:
            try:
                async with websockets.connect(url) as websocket:
                    logging.debug("Connected to Binance Websocket successfully.")
                    self.retry_count = 0  # Reset retry count on successful connection

                    # Inner loop to keep receiving messages as long as the connection is open
                    while True:
                        try:
                            message = await websocket.recv()
                            ticker_data = json.loads(message)

                            # Process the price nd send alerts as needed
                            current_price = float(ticker_data["c"])
                            volume = float(ticker_data["v"])

                            await self.process_price(current_price, volume)

                        except Exception as e:
                            # Increment retry count only for major errors
                            logging.warning("Intermediate WebSocket error: %s", e)
                            self.retry_count = min(
                                self.retry_count + 1, self.max_retries
                            )
                            # # Handle internal WebSocket errors
                            # if self.retry_count >= self.max_retries:
                            #     error_message = f"PriceAlertBot - WebSocket failed after {self.max_retries} retries. Stopping..."
                            #     logging.error(
                            #         "WebSocket error occurred: %s",
                            #         error_message,
                            #         exc_info=True,
                            #     )
                            #     self.send_error_report(error_message)
                            #     return  # Exit the function if maximum retries are reached

                            # # Log the error and retry
                            # error_message = f"PriceAlertBot - WebSocket Error: {e}. Reconnecting in {2 ** self.retry_count} seconds..."
                            # logging.error(
                            #     "WebSocket error occurred: %s",
                            #     error_message,
                            #     exc_info=True,
                            # )
                            # self.send_error_report(error_message)

                            # self.retry_count += 1

                            # Wait before retrying to receive data (exponential backoff)
                            await asyncio.sleep(2**self.retry_count)
                            break  # Exit inner loop to reconnect

            except (
                websockets.exceptions.ConnectionClosed,
                websockets.exceptions.WebSocketException,
            ) as e:
                # Log the connection issue
                logging.error(
                    "PriceAlertBot - WebSocket connection error: %s. Reconnecting...",
                    e,
                    exc_info=True,
                )
                self.retry_count += 1
                if self.retry_count >= self.max_retries:
                    self.send_error_report("Max retries reached. Stopping WebSocket.")
                    return
                await asyncio.sleep(2**self.retry_count)

                # # Wait before reconnection (exponential backoff strategy)
                # for attempt in range(5):
                #     try:
                #         await asyncio.sleep(2**attempt)
                #         break
                #     except asyncio.CancelledError:
                #         return

            except Exception as e:
                # Log unexpected exceptions
                logging.error("Unexpected error occurred: %s", e, exc_info=True)
                self.retry_count += 1
                if self.retry_count >= self.max_retries:
                    self.send_error_report("Max retries reached. Stopping WebSocket.")
                    return

                await asyncio.sleep(2**self.retry_count)

    async def process_price(self, current_price, volume):
        # Code to process the price calculate the difference, and send alerts as needed
        last_price = self.config.shared_state["last_price"]

        if last_price:
            price_change_percentage = abs(current_price - last_price) / last_price

            # Calculate the rounded price change threshold
            # This logic triggers an alert if the price crosses a rounded threshold (e.g., from x,1000 to x+1,1000 or x-1,1000)
            rounded_price_change = abs(
                math.floor(last_price / 1000) * 1000
                - math.floor(current_price / 1000) * 1000
            )

            # if price_change_percentage >= self.price_change_percentage:
            if (
                rounded_price_change == self.config.ROUNDED_PRICE_CHANGE
            ):  # only trigger alerts if the price change from X,kkk to {X+1},kkk or {X-1},kkk, e.g., 95,270 to 96,100 or 94290 to 91800
                # Add the new row to the data batch
                current_time = time.strftime("%Y/%m/%d %H:%M:%S", time.gmtime())
                self.data_batch.append(
                    [
                        current_time,
                        self.ticker.upper(),
                        last_price,
                        current_price,
                        price_change_percentage,
                        volume,
                    ]
                )

                # Telegram Telegram alert
                self.alert_price_change(
                    current_price,
                    last_price,
                    price_change_percentage,
                    volume,
                )

                # Check if batch needs to be flushed
                self.flush_data_if_needed()

        # Update the last price in the shared state
        self.config.shared_state["last_price"] = current_price

    def flush_data_if_needed(self):
        # Check if we need to flush the batch data to Google Sheets
        current_time = time.time()

        if (
            len(self.data_batch) >= self.batch_limit
            or (current_time - self.last_batch_update_time) >= 300
        ):
            self.flush_data_to_google_sheets()

    def flush_data_to_google_sheets(self):
        if not self.data_batch:
            return

        try:
            # Use append_rows to add multiple rows in one batch to Google Sheets
            self.sheet.append_rows(self.data_batch, value_input_option="RAW")

            logging.info(
                "Successfully updated Google Sheets with %d rows", len(self.data_batch)
            )

            # Clear the batch data
            self.data_batch.clear()
            self.last_batch_update_time = time.time()

        except Exception as e:
            logging.error(
                "Failed to update to Google Sheets in batch: %s", e, exc_info=True
            )

    # Method to send a message to Telegram
    def send_telegram_message(self, message):
        url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
        params = {
            "chat_id": self.telegram_chat_id,
            "text": message,
            "parse_mode": "HTML",
        }

        try:
            response = requests.post(url, params=params, timeout=30)
            response.raise_for_status()  # Will raise an HTTPError if the request failed
            logging.info("Successfully sent Telegram message")
        except requests.exceptions.RequestException as e:
            logging.error(
                "Failed to send Telegram message: %s",
                e,
                exc_info=True,
            )

    def send_error_report(self, message):
        url = f"https://api.telegram.org/bot{self.config.ERROR_REPORT_BOT_TOKEN}/sendMessage"
        params = {
            "chat_id": self.config.ERROR_REPORT_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
        }

        requests.post(url=url, params=params, timeout=60)

    # Helper function to handle price change alert
    def alert_price_change(
        self, current_price, last_price, price_change_percentage, volume
    ):
        # Get the current time for use in sending alerts
        current_timestamp = time.time()

        if current_timestamp - self.last_telegram_alert_time >= 10:
            # Format the prices and create the alert message
            formatted_last_price = f"{last_price:,.2f}"
            formatted_current_price = f"{current_price:,.2f}"

            change_direction_symbol = "⬆️" if current_price > last_price else "🔻"
            message = (
                f"<b><u>{self.ticker.upper()}</u></b> {change_direction_symbol} <b>{(price_change_percentage * 100):,.2f}%</b>\n"
                f"From {formatted_last_price} To <b><u>{formatted_current_price}</u></b>\n"
                f"Trading Volume: <u>{volume}</u>"
            )

            logging.info("Sending Telegram message: %s", message)

            # Send message via Telegram
            self.send_telegram_message(message)

            # Update the last alert time
            self.last_telegram_alert_time = current_timestamp

        else:
            logging.debug("Skipping alert due to cool-down period.")


# if __name__ == "__main__":
#     bot = PriceAlertBot(config)

#     # message = "BTCUSDC ⬆️ 0.01%\n" "From last_price To current_price"

#     alert_message = (
#         "<b><u>BTCUSDC</u></b> ❓ <b>0.001%</b>\n"
#         "From last_price To <b><u>current_price</u></b>\n"
#         "Trading Volume: <u>Volume</u>"
#     )

#     bot.send_telegram_message(alert_message)

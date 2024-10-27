import time
import config
from price_alert_bot import PriceAlertBot

# Create an instance of the bot with dependency injection
bot = PriceAlertBot(config)

# Main loop to check the price every 30 seconds
while True:
    bot.check_price()
    time.sleep(config.SLEEP_TIME)

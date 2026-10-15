# import time
import asyncio
import config
from price_alert_bot import PriceAlertBot

# if __name__ == "__main__":
#     # Create an instance of the bot with dependency injection
#     bot = PriceAlertBot(config)

#     # Main loop to check the price every 30 seconds
#     while True:
#         bot.check_price()
#         time.sleep(config.SLEEP_TIME)


# Start the WebSocket listener
def main():
    bot = PriceAlertBot(config)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(bot.listen_to_binance())


if __name__ == "__main__":
    main()

# x = 95500
# y = 3

# print((x // 10**y) * 10**y)
# -------------------------------------
# nums = [2, 3, 2, 6, 6, 3, 2, 3, 2, 3, 6]
# unique = 0
# for n in nums:
#     unique ^= n

# print(unique)

# -------------------------------------
import asyncio
import websockets


async def test_ws():
    url = "wss://stream.binance.com:9443/ws/btcusdc@ticker"
    async with websockets.connect(url) as websocket:
        response = await websocket.recv()
        print(response)


asyncio.run(test_ws())

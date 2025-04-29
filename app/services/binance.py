import requests

from app.database.init_engine import AsyncSessionLocal

async def get_prices(pair):
    async with AsyncSessionLocal() as session:
        response = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={pair}")
        data = response.json()
    return data


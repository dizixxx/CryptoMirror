import aiohttp
from typing import Dict, Any

async def get_prices(pairs: list) -> Dict[str, Any]:
    url = "https://api.binance.com/api/v3/ticker/price"
    params = {'symbols': '["' + '","'.join(pairs) + '"]'}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            data = await response.json()
            return {item['symbol']: float(item['price']) for item in data}
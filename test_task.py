"""
    Description: For an exchange, get all trading pairs, their latest prices and trading volume for 24 hours
    Task:
        Create a class inherited from the BaseExchange class.
        Write the implementation of the methods and fill in the required fields
    Note:
        Feel free to add another internal methods.
        It is important that the example from the main function runs without errors
    The flow looks like this:
        1. Request data from the exchange
        2. We bring the ticker to the general format
        3. We extract from the ticker properties the last price,
            the 24-hour trading volume of the base currency
            and the 24-hour trading volume of the quoted currency.
            (at least one of the volumes is required)
        4. Return the structure in the format:
            {
                "BTC/USDT": TickerInfo(last=57000, baseVolume=11328, quoteVolume=3456789),
                "ETH/BTC": TickerInfo(last=4026, baseVolume=4567, quoteVolume=0)
            }
"""
import asyncio
import aiohttp
from dataclasses import dataclass
# Импорты



@dataclass
class TickerInfo:
    last: float  # Last price
    baseVolume: float  # Base currency volume_24h
    quoteVolume: float  # Target currency volume_24h
#type

Symbol = str  # Trading pair like ETH/USDT


class BaseExchange: #Базовый класс/Родительский класс
    async def fetch_data(self, url: str):
        """
        :param url: URL to fetch the data from exchange
        :return: raw data
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp and resp.status == 200:
                    data = await resp.json()
                else:
                    raise Exception(resp)
        return data

    async def fetch_tickers(self) -> dict[Symbol, TickerInfo]:
        """
            Method fetch data from exchange and return all tickers in normalized format
            :return:
        """
        raise NotImplementedError


    def normalize_data(self, data: dict) -> dict[Symbol, TickerInfo]:
        """
            :param data: raw data received from the exchange
            :return: normalized data in a common format
        """
        raise NotImplementedError

    def _convert_symbol_to_ccxt(self, symbols: str) -> Symbol:
        """
            Trading pairs from the exchange can come in various formats like: btc_usdt, BTCUSDT, etc.
            Here we convert them to a value like: BTC/USDT.
            The format is as follows: separator "/" and all characters in uppercase

            :param symbols: Trading pair ex.: BTC_USDT
            :return: BTC/USDT
        """
        raise NotImplementedError

    async def load_markets(self):
        """
            Sometimes the exchange does not have a route to receive all the tickers at once.
            In this case, you first need to get a list of all trading pairs and save them to self.markets.(Ex.2)
            And then get all these tickers one at a time.
            Allow for delays between requests so as not to exceed the limits
            (you can find the limits in the documentation for the exchange API)
        """

    async def close(self):
        pass  # stub, not really needed


class MyExchange(BaseExchange):
    """
        docs: https://docs.coingecko.com/v3.0.1/reference/exchanges
    """

    def __init__(self):
        self.id = "BitStorage"
        self.base_url = "https://api.coingecko.com/"
        self.markets = {}
        self.key = "CG-2y7UoUVNrPC6aLn62hXsJuGd" # it`s apikey

    async def fetch_data(self, url: str):
        """
        :param url: URL to fetch the data from exchange
        :return: raw data
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers={"x-cg-demo-api-key": self.key}) as resp:
                if resp and resp.status == 200:
                    data = await resp.json()
                else:
                    raise Exception(resp)
        return data

    def _convert_symbol_to_ccxt(self, symbols: str) -> Symbol:
        if isinstance(symbols, str):
            symbols = symbols.replace("_", "/")
            return symbols
        raise TypeError(f"{symbols} invalid type")

    def normalize_data(self, data: dict) -> dict[Symbol, TickerInfo]:
        result = {}
        for ticker in data:
            symbols = ticker["base"] + "_" + ticker["target"]
            key = self._convert_symbol_to_ccxt(symbols)
            obj = TickerInfo(
                last=float(ticker["last"]),
                baseVolume=float(ticker["volume"]),
                quoteVolume=float(ticker["converted_volume"].get("usd", 0)),
            )

            result[key] = obj
        return result

    async def fetch_tickers(self) -> dict[Symbol, TickerInfo]:
        fetched_exchange = await self.fetch_data(self.base_url + "api/v3/exchanges/" + self.id + "/tickers" + "?coin_ids=USDT")
        tickers = fetched_exchange.get("tickers", [])
        data = self.normalize_data(tickers)
        return data

    async def load_markets(self):
        data = await self.fetch_data(self.base_url + "api/v3/exchanges/" + self.id)
        tickers = data.get("tickers", [])
        for ticker in tickers:
            base = ticker["base"]
            quote = ticker["target"]
            symbols = base + "_" + quote
            key = self._convert_symbol_to_ccxt(symbols)
            self.markets[key] = base + quote




# EXAMPLE 1

class biconomy(BaseExchange):
    """
        docs: https://github.com/BiconomyOfficial/apidocs?tab=readme-ov-file#Getting-Started
    """

    def __init__(self):
        self.id = 'biconomy'
        self.base_url = "https://www.biconomy.com/"
        self.markets = {}  # not really needed, just a stub

    async def fetch_tickers(self) -> dict[str, TickerInfo]:
        data = await self.fetch_data(self.base_url + 'api/v1/tickers')
        return self.normalize_data(data)

    def _convert_symbol_to_ccxt(self, symbols: str) -> Symbol:
        if isinstance(symbols, str):
            symbols = symbols.replace("_", "/")
            return symbols
        raise TypeError(f"{symbols} invalid type")

    def normalize_data(self, data: dict) -> dict[Symbol, TickerInfo]:
        normalized_data = {}
        tickers = data.get('ticker', [])
        for ticker in tickers:
            symbol = self._convert_symbol_to_ccxt(ticker.get("symbol", ''))
            normalized_data[symbol] = TickerInfo(last=float(ticker.get("last", 0)),
                                                 baseVolume=float(ticker.get("vol", 0)),
                                                 quoteVolume=0)
        return normalized_data


# Example 2  (with load markets)

class toobit(BaseExchange):
    """
        docs: https://toobit-docs.github.io/apidocs/spot/v1/en/#24hr-ticker-price-change-statistics
    """

    def __init__(self):
        self.id = 'toobit'
        self.base_url = "https://api.toobit.com/"
        self.markets = {}

    async def fetch_tickers(self) -> dict[Symbol, TickerInfo]:
        if not self.markets:
            await self.load_markets()

        result = {}
        for symbol in self.markets.values():
            print(f"Fetching: {symbol}")
            data = await self.fetch_data(self.base_url + 'quote/v1/ticker/24hr?symbol=' + symbol)
            result.update(self.normalize_data(data))
        return result

    async def load_markets(self):
        data = await self.fetch_data(self.base_url + "api/v1/exchangeInfo")
        symbols = data.get("symbols", [])
        for symbol in symbols:
            base = symbol["baseAsset"]
            quote = symbol["quoteAsset"]
            if base and quote:
                self.markets[base + "/" + quote] = base + quote

    def normalize_data(self, data: list) -> dict[Symbol, TickerInfo]:
        normalized_data = {}
        result = data[0]
        symbol = self._convert_symbol_to_ccxt(result.get("s"))
        normalized_data[symbol] = TickerInfo(last=float(result.get("c", 0)),
                                             baseVolume=float(result.get("v", 0)),
                                             quoteVolume=float(result.get("qv", 0)))
        return normalized_data

    def _convert_symbol_to_ccxt(self, symbols: str) -> Symbol:
        if isinstance(symbols, str):
            if symbols.endswith("USDT"):
                symbols = symbols.replace("USDT", "/USDT")
            return symbols
        raise TypeError(f"{symbols} invalid type")


async def main():
    """
        Test yourself here. Verify prices and volumes here: https://www.coingecko.com/
    """
    exchange = MyExchange()
    # exchange = biconomy()
    # exchange = toobit()
    await exchange.load_markets()

    tickers = await exchange.fetch_tickers()

    for symbol, prop in tickers.items():
        print(symbol, prop)

    assert isinstance(tickers, dict)
    for symbol, prop in tickers.items():
        assert isinstance(prop, TickerInfo)
        assert isinstance(symbol, Symbol)

if __name__ == "__main__":
    asyncio.run(main())

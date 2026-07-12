import unittest
from unittest.mock import patch

from tools.stock_fetcher import fetch_tickers_live


class StockFetcherTests(unittest.TestCase):
    @patch("tools.stock_fetcher.yf.screen", side_effect=Exception("screener down"))
    def test_fetch_tickers_live_returns_fallback_when_screener_fails(self, _mock_screen):
        tickers = fetch_tickers_live(count=5)
        self.assertEqual(tickers, [
            "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS"
        ])


if __name__ == "__main__":
    unittest.main()

from ib_insync import IB, Stock, Contract, util
from typing import Optional, List
from datetime import date
import threading
import asyncio


class IBKRService:
    def __init__(self):
        self.ib: Optional[IB] = None
        self.connected = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None

    def _run_event_loop(self, loop: asyncio.AbstractEventLoop):
        """Run the event loop in a separate thread."""
        asyncio.set_event_loop(loop)
        loop.run_forever()

    def connect_sync(self, host: str = "127.0.0.1", port: int = 7497, client_id: int = 1) -> bool:
        """
        Connect to TWS or IB Gateway.

        Ports:
        - TWS Live: 7496
        - TWS Paper: 7497
        - IB Gateway Live: 4001
        - IB Gateway Paper: 4002
        """
        try:
            if self.ib and self.ib.isConnected():
                return True

            # Create a new event loop for ib_insync in a separate thread
            self._loop = asyncio.new_event_loop()
            self._thread = threading.Thread(target=self._run_event_loop, args=(self._loop,), daemon=True)
            self._thread.start()

            # Create IB instance and connect using the dedicated loop
            self.ib = IB()

            # Run the connection in the dedicated event loop
            future = asyncio.run_coroutine_threadsafe(
                self._connect_async(host, port, client_id),
                self._loop
            )
            self.connected = future.result(timeout=10)
            return self.connected
        except Exception as e:
            print(f"Failed to connect to IBKR: {e}")
            self.connected = False
            return False

    async def _connect_async(self, host: str, port: int, client_id: int) -> bool:
        """Async connection helper."""
        try:
            await self.ib.connectAsync(host, port, clientId=client_id)
            if self.ib.isConnected():
                # Request account updates to populate portfolio data
                self.ib.reqAccountUpdates(True, '')
                await asyncio.sleep(2)  # Wait for account data to populate
            return self.ib.isConnected()
        except Exception as e:
            print(f"Async connect error: {e}")
            return False

    def disconnect(self):
        """Disconnect from IBKR."""
        if self.ib and self.connected:
            if self._loop and self._loop.is_running():
                future = asyncio.run_coroutine_threadsafe(
                    self._disconnect_async(),
                    self._loop
                )
                try:
                    future.result(timeout=5)
                except:
                    pass
                # Stop the event loop
                self._loop.call_soon_threadsafe(self._loop.stop)
            self.connected = False

    async def _disconnect_async(self):
        """Async disconnect helper."""
        if self.ib:
            self.ib.disconnect()

    def is_connected(self) -> bool:
        """Check if connected to IBKR."""
        if self.ib is None:
            return False
        try:
            return self.ib.isConnected()
        except:
            return False

    def _run_in_loop(self, coro, timeout=10):
        """Run a coroutine in the dedicated event loop."""
        if not self._loop or not self._loop.is_running():
            raise ConnectionError("Event loop not running")
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=timeout)

    def get_positions(self) -> List[dict]:
        """Get all positions from IBKR account."""
        if not self.is_connected():
            raise ConnectionError("Not connected to IBKR")

        positions = self._run_in_loop(self._get_positions_async())
        return positions

    async def _get_positions_async(self) -> List[dict]:
        """Async helper to get positions."""
        positions = self.ib.positions()
        result = []

        for pos in positions:
            contract = pos.contract

            # Determine asset type
            asset_type = "stock"
            if contract.secType == "STK":
                asset_type = "stock"
            elif contract.secType == "ETF":
                asset_type = "etf"
            elif contract.secType == "BOND":
                asset_type = "bond"
            elif contract.secType == "CASH":
                asset_type = "cash"
            elif contract.secType == "CRYPTO":
                asset_type = "crypto"
            else:
                asset_type = "other"

            result.append({
                "symbol": contract.symbol,
                "shares": pos.position,
                "avg_cost": pos.avgCost,
                "cost_basis": pos.position * pos.avgCost,
                "asset_type": asset_type,
                "currency": contract.currency,
                "exchange": contract.exchange,
                "sec_type": contract.secType,
                "con_id": contract.conId
            })

        return result

    def get_account_summary(self) -> dict:
        """Get account summary from IBKR."""
        if not self.is_connected():
            raise ConnectionError("Not connected to IBKR")

        return self._run_in_loop(self._get_account_summary_async())

    async def _get_account_summary_async(self) -> dict:
        """Async helper to get account summary."""
        account_values = self.ib.accountValues()

        summary = {"by_currency": {}}
        tags_of_interest = ["NetLiquidation", "TotalCashValue", "GrossPositionValue",
                           "UnrealizedPnL", "RealizedPnL", "BuyingPower"]

        for av in account_values:
            if av.tag in tags_of_interest:
                currency = av.currency if av.currency else "BASE"
                if currency not in summary["by_currency"]:
                    summary["by_currency"][currency] = {}
                summary["by_currency"][currency][av.tag] = float(av.value)

                # Also keep USD/BASE at top level for backwards compatibility
                if currency in ["USD", "BASE"]:
                    summary[av.tag] = float(av.value)

        return summary

    def get_market_price(self, symbol: str, sec_type: str = "STK", exchange: str = "SMART", currency: str = "USD") -> Optional[float]:
        """Get current market price for a symbol."""
        if not self.is_connected():
            raise ConnectionError("Not connected to IBKR")

        return self._run_in_loop(self._get_market_price_async(symbol, exchange, currency), timeout=15)

    async def _get_market_price_async(self, symbol: str, exchange: str, currency: str) -> Optional[float]:
        """Async helper to get market price."""
        contract = Stock(symbol, exchange, currency)
        self.ib.qualifyContracts(contract)

        # Request market data
        ticker = self.ib.reqMktData(contract)
        await asyncio.sleep(2)  # Wait for data

        price = ticker.marketPrice()

        # Cancel market data subscription
        self.ib.cancelMktData(contract)

        return price if price and price > 0 else None

    def get_portfolio(self) -> List[dict]:
        """Get portfolio with current market values."""
        if not self.is_connected():
            raise ConnectionError("Not connected to IBKR")

        return self._run_in_loop(self._get_portfolio_async())

    async def _get_portfolio_async(self) -> List[dict]:
        """Async helper to get portfolio."""
        portfolio = self.ib.portfolio()
        result = []

        for item in portfolio:
            contract = item.contract

            asset_type = "stock"
            if contract.secType == "STK":
                asset_type = "stock"
            elif contract.secType == "ETF":
                asset_type = "etf"
            elif contract.secType == "BOND":
                asset_type = "bond"
            elif contract.secType == "CASH":
                asset_type = "cash"
            elif contract.secType == "CRYPTO":
                asset_type = "crypto"
            else:
                asset_type = "other"

            result.append({
                "symbol": contract.symbol,
                "shares": item.position,
                "market_price": item.marketPrice,
                "market_value": item.marketValue,
                "avg_cost": item.averageCost,
                "cost_basis": item.position * item.averageCost,
                "unrealized_pnl": item.unrealizedPNL,
                "realized_pnl": item.realizedPNL,
                "asset_type": asset_type,
                "currency": contract.currency
            })

        return result


# Global instance
ibkr_service = IBKRService()

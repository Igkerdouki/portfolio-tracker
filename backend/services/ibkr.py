from ib_insync import IB, Stock, Contract
from typing import Optional, List
import asyncio
from datetime import date


class IBKRService:
    def __init__(self):
        self.ib: Optional[IB] = None
        self.connected = False

    async def connect(self, host: str = "127.0.0.1", port: int = 7497, client_id: int = 1) -> bool:
        """
        Connect to TWS or IB Gateway.

        Ports:
        - TWS Live: 7496
        - TWS Paper: 7497
        - IB Gateway Live: 4001
        - IB Gateway Paper: 4002
        """
        try:
            self.ib = IB()
            await self.ib.connectAsync(host, port, clientId=client_id)
            self.connected = self.ib.isConnected()
            return self.connected
        except Exception as e:
            print(f"Failed to connect to IBKR: {e}")
            self.connected = False
            return False

    def connect_sync(self, host: str = "127.0.0.1", port: int = 7497, client_id: int = 1) -> bool:
        """Synchronous connection to TWS or IB Gateway."""
        try:
            self.ib = IB()
            self.ib.connect(host, port, clientId=client_id)
            self.connected = self.ib.isConnected()
            return self.connected
        except Exception as e:
            print(f"Failed to connect to IBKR: {e}")
            self.connected = False
            return False

    def disconnect(self):
        """Disconnect from IBKR."""
        if self.ib and self.connected:
            self.ib.disconnect()
            self.connected = False

    def is_connected(self) -> bool:
        """Check if connected to IBKR."""
        return self.ib is not None and self.ib.isConnected()

    def get_positions(self) -> List[dict]:
        """Get all positions from IBKR account."""
        if not self.is_connected():
            raise ConnectionError("Not connected to IBKR")

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

        # Request account values
        account_values = self.ib.accountValues()

        summary = {}
        for av in account_values:
            if av.tag in ["NetLiquidation", "TotalCashValue", "GrossPositionValue",
                          "UnrealizedPnL", "RealizedPnL", "BuyingPower"]:
                if av.currency == "USD" or av.currency == "BASE":
                    summary[av.tag] = float(av.value)

        return summary

    def get_market_price(self, symbol: str, sec_type: str = "STK", exchange: str = "SMART", currency: str = "USD") -> Optional[float]:
        """Get current market price for a symbol."""
        if not self.is_connected():
            raise ConnectionError("Not connected to IBKR")

        contract = Stock(symbol, exchange, currency)
        self.ib.qualifyContracts(contract)

        # Request market data
        ticker = self.ib.reqMktData(contract)
        self.ib.sleep(2)  # Wait for data

        price = ticker.marketPrice()

        # Cancel market data subscription
        self.ib.cancelMktData(contract)

        return price if price and price > 0 else None

    def get_portfolio(self) -> List[dict]:
        """Get portfolio with current market values."""
        if not self.is_connected():
            raise ConnectionError("Not connected to IBKR")

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

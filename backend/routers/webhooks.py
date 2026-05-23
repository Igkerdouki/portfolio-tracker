"""
TradingView Webhook Integration
Receives alerts from TradingView and routes them to the agentic system.
"""

from fastapi import APIRouter, HTTPException, Request, Header
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
import json
import hashlib
import hmac
import os

from agents import AgentRole, Message, MessageType
from agents.orchestrator import TradingSystem

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# Webhook secret for validation (set in .env)
WEBHOOK_SECRET = os.getenv("TRADINGVIEW_WEBHOOK_SECRET", "your-secret-key")

# Store for recent webhooks (deduplication)
_recent_webhooks: Dict[str, datetime] = {}


class TradingViewAlert(BaseModel):
    """
    TradingView webhook payload format.

    Configure your TradingView alert message like:
    {
        "symbol": "{{ticker}}",
        "action": "BUY",
        "price": {{close}},
        "time": "{{time}}",
        "exchange": "{{exchange}}",
        "interval": "{{interval}}",
        "strategy": "My Strategy",
        "message": "Golden cross detected"
    }
    """
    symbol: str
    action: str  # BUY, SELL, CLOSE
    price: Optional[float] = None
    time: Optional[str] = None
    exchange: Optional[str] = None
    interval: Optional[str] = None
    strategy: Optional[str] = None
    message: Optional[str] = None
    # Optional fields for more context
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    quantity: Optional[float] = None
    confidence: Optional[float] = None


class WebhookResponse(BaseModel):
    status: str
    message: str
    signal_id: Optional[str] = None


def validate_webhook(payload: str, signature: str) -> bool:
    """Validate webhook signature if secret is configured."""
    if WEBHOOK_SECRET == "your-secret-key":
        return True  # Skip validation if default secret

    expected = hmac.new(
        WEBHOOK_SECRET.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature, expected)


def deduplicate_webhook(alert: TradingViewAlert) -> bool:
    """Check if this is a duplicate webhook (within 5 seconds)."""
    key = f"{alert.symbol}_{alert.action}_{alert.price}"
    now = datetime.now()

    # Clean old entries
    expired = [k for k, v in _recent_webhooks.items() if (now - v).seconds > 60]
    for k in expired:
        del _recent_webhooks[k]

    # Check for duplicate
    if key in _recent_webhooks:
        if (now - _recent_webhooks[key]).seconds < 5:
            return True  # Duplicate

    _recent_webhooks[key] = now
    return False


@router.post("/tradingview", response_model=WebhookResponse)
async def tradingview_webhook(
    request: Request,
    x_signature: Optional[str] = Header(None, alias="X-TradingView-Signature"),
):
    """
    Receive TradingView alert webhooks.

    Configure in TradingView:
    1. Create alert on your indicator/strategy
    2. Set webhook URL to: https://your-domain.com/webhooks/tradingview
    3. Set alert message to JSON format (see TradingViewAlert model)

    Example alert message:
    {
        "symbol": "{{ticker}}",
        "action": "BUY",
        "price": {{close}},
        "time": "{{time}}",
        "interval": "{{interval}}",
        "strategy": "Golden Cross",
        "message": "SMA20 crossed above SMA50"
    }
    """
    try:
        # Get raw body for signature validation
        body = await request.body()
        body_str = body.decode()

        # Validate signature if provided
        if x_signature and not validate_webhook(body_str, x_signature):
            raise HTTPException(status_code=401, detail="Invalid signature")

        # Parse the alert
        try:
            data = json.loads(body_str)
            alert = TradingViewAlert(**data)
        except json.JSONDecodeError:
            # Try to parse as plain text (simple format)
            alert = parse_simple_alert(body_str)

        # Check for duplicates
        if deduplicate_webhook(alert):
            return WebhookResponse(
                status="duplicate",
                message="Duplicate alert ignored"
            )

        # Process the alert
        signal_id = await process_tradingview_alert(alert)

        return WebhookResponse(
            status="success",
            message=f"Alert processed: {alert.action} {alert.symbol}",
            signal_id=signal_id
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


def parse_simple_alert(text: str) -> TradingViewAlert:
    """
    Parse simple text alerts like:
    "BUY AAPL at 150.25"
    "SELL MSFT"
    """
    parts = text.strip().upper().split()

    if len(parts) < 2:
        raise ValueError("Invalid alert format")

    action = parts[0]
    symbol = parts[1]
    price = None

    if "AT" in parts and len(parts) > parts.index("AT") + 1:
        try:
            price = float(parts[parts.index("AT") + 1])
        except:
            pass

    return TradingViewAlert(
        symbol=symbol,
        action=action,
        price=price,
        message=text
    )


async def process_tradingview_alert(alert: TradingViewAlert) -> str:
    """Process alert and route to trading system."""
    from routers.agents import get_system

    system = get_system()

    # Create signal from alert
    signal = {
        "symbol": alert.symbol.upper(),
        "action": alert.action.upper(),
        "signal": alert.action.upper(),  # For compatibility
        "price": alert.price,
        "source": "tradingview",
        "strategy": alert.strategy,
        "message": alert.message,
        "interval": alert.interval,
        "exchange": alert.exchange,
        "stop_loss": alert.stop_loss,
        "take_profit": alert.take_profit,
        "quantity": alert.quantity,
        "confidence": alert.confidence or 0.7,  # Default confidence for TV signals
        "timestamp": datetime.now().isoformat(),
        "received_at": datetime.now().isoformat(),
    }

    signal_id = f"tv_{datetime.now().timestamp()}"

    # Create message for orchestrator
    message = Message(
        id=signal_id,
        sender=AgentRole.SCANNER,  # Treat TV as external scanner
        recipient=AgentRole.ORCHESTRATOR,
        msg_type=MessageType.SIGNAL,
        payload=signal,
        priority=8,  # High priority for external signals
    )

    # Route to orchestrator
    if system.orchestrator.running:
        await system.orchestrator.route_message(message)
    else:
        # Queue for when system starts
        system.orchestrator.pending_signals.append(signal)

    # Log the alert
    print(f"[TradingView] Alert received: {alert.action} {alert.symbol} @ {alert.price}")

    return signal_id


@router.post("/tradingview/test")
async def test_webhook(alert: TradingViewAlert):
    """Test endpoint to simulate TradingView webhook."""
    signal_id = await process_tradingview_alert(alert)
    return {
        "status": "success",
        "signal_id": signal_id,
        "alert": alert.dict()
    }


@router.get("/tradingview/recent")
async def get_recent_webhooks():
    """Get recent webhook activity."""
    return {
        "recent_alerts": len(_recent_webhooks),
        "keys": list(_recent_webhooks.keys())[-10:],
    }


# ============================================================
# PINE SCRIPT EXAMPLES
# ============================================================

PINE_SCRIPT_EXAMPLES = '''
// ============================================================
// PINE SCRIPT WEBHOOK EXAMPLES
// Copy these to TradingView and customize for your strategy
// ============================================================

// --------------------------
// EXAMPLE 1: Simple Moving Average Crossover
// --------------------------
//@version=5
strategy("MA Crossover Webhook", overlay=true)

// Parameters
fast_length = input.int(20, "Fast MA Length")
slow_length = input.int(50, "Slow MA Length")

// Calculate MAs
fast_ma = ta.sma(close, fast_length)
slow_ma = ta.sma(close, slow_length)

// Plot
plot(fast_ma, "Fast MA", color.blue)
plot(slow_ma, "Slow MA", color.red)

// Signals
buy_signal = ta.crossover(fast_ma, slow_ma)
sell_signal = ta.crossunder(fast_ma, slow_ma)

// Strategy entries
if buy_signal
    strategy.entry("Long", strategy.long)

if sell_signal
    strategy.close("Long")

// Alerts with webhook message format
alertcondition(buy_signal, "Buy Signal", '{"symbol": "{{ticker}}", "action": "BUY", "price": {{close}}, "time": "{{time}}", "interval": "{{interval}}", "strategy": "MA Crossover", "message": "Fast MA crossed above Slow MA"}')

alertcondition(sell_signal, "Sell Signal", '{"symbol": "{{ticker}}", "action": "SELL", "price": {{close}}, "time": "{{time}}", "interval": "{{interval}}", "strategy": "MA Crossover", "message": "Fast MA crossed below Slow MA"}')


// --------------------------
// EXAMPLE 2: RSI + MACD Combined
// --------------------------
//@version=5
indicator("RSI MACD Scanner", overlay=false)

// RSI
rsi_length = input.int(14, "RSI Length")
rsi = ta.rsi(close, rsi_length)
rsi_oversold = 30
rsi_overbought = 70

// MACD
[macd_line, signal_line, hist] = ta.macd(close, 12, 26, 9)

// Combined signals
buy_signal = rsi < rsi_oversold and ta.crossover(macd_line, signal_line)
sell_signal = rsi > rsi_overbought and ta.crossunder(macd_line, signal_line)

// Plot
plot(rsi, "RSI", color.purple)
hline(rsi_oversold, "Oversold", color.green)
hline(rsi_overbought, "Overbought", color.red)

// Alerts
alertcondition(buy_signal, "RSI MACD Buy", '{"symbol": "{{ticker}}", "action": "BUY", "price": {{close}}, "time": "{{time}}", "strategy": "RSI MACD", "message": "RSI oversold + MACD bullish cross", "confidence": 0.8}')

alertcondition(sell_signal, "RSI MACD Sell", '{"symbol": "{{ticker}}", "action": "SELL", "price": {{close}}, "time": "{{time}}", "strategy": "RSI MACD", "message": "RSI overbought + MACD bearish cross", "confidence": 0.8}')


// --------------------------
// EXAMPLE 3: Multi-Timeframe Scanner
// --------------------------
//@version=5
indicator("MTF Scanner", overlay=true)

// Get higher timeframe data
htf = input.timeframe("D", "Higher Timeframe")
htf_close = request.security(syminfo.tickerid, htf, close)
htf_sma = request.security(syminfo.tickerid, htf, ta.sma(close, 20))

// Current timeframe
ltf_sma = ta.sma(close, 20)
ltf_rsi = ta.rsi(close, 14)

// Aligned signal: HTF trend + LTF entry
htf_bullish = htf_close > htf_sma
htf_bearish = htf_close < htf_sma
ltf_entry = ta.crossover(close, ltf_sma) and ltf_rsi < 60
ltf_exit = ta.crossunder(close, ltf_sma) and ltf_rsi > 40

buy_signal = htf_bullish and ltf_entry
sell_signal = htf_bearish and ltf_exit

// Visual
bgcolor(htf_bullish ? color.new(color.green, 90) : color.new(color.red, 90))
plotshape(buy_signal, "Buy", shape.triangleup, location.belowbar, color.green)
plotshape(sell_signal, "Sell", shape.triangledown, location.abovebar, color.red)

// Webhook alerts
alertcondition(buy_signal, "MTF Buy", '{"symbol": "{{ticker}}", "action": "BUY", "price": {{close}}, "strategy": "MTF Scanner", "interval": "{{interval}}", "message": "HTF bullish + LTF entry signal", "confidence": 0.85}')

alertcondition(sell_signal, "MTF Sell", '{"symbol": "{{ticker}}", "action": "SELL", "price": {{close}}, "strategy": "MTF Scanner", "interval": "{{interval}}", "message": "HTF bearish + LTF exit signal", "confidence": 0.85}')


// --------------------------
// EXAMPLE 4: With Stop Loss & Take Profit
// --------------------------
//@version=5
strategy("Risk Managed Strategy", overlay=true)

// Entry conditions
ema20 = ta.ema(close, 20)
ema50 = ta.ema(close, 50)
buy_signal = ta.crossover(ema20, ema50)
sell_signal = ta.crossunder(ema20, ema50)

// Risk parameters
atr = ta.atr(14)
stop_loss_mult = input.float(1.5, "Stop Loss ATR Multiplier")
take_profit_mult = input.float(3.0, "Take Profit ATR Multiplier")

// Calculate levels
stop_loss = close - (atr * stop_loss_mult)
take_profit = close + (atr * take_profit_mult)

// Strategy
if buy_signal
    strategy.entry("Long", strategy.long)
    strategy.exit("Exit", "Long", stop=stop_loss, limit=take_profit)

// Webhook with risk levels
alertcondition(buy_signal, "Buy with Risk", '{"symbol": "{{ticker}}", "action": "BUY", "price": {{close}}, "stop_loss": ' + str.tostring(stop_loss) + ', "take_profit": ' + str.tostring(take_profit) + ', "strategy": "Risk Managed", "confidence": 0.75}')
'''


@router.get("/tradingview/pine-examples")
async def get_pine_examples():
    """Get example Pine Script code for TradingView webhooks."""
    return {
        "instructions": """
## Setting Up TradingView Webhooks

### Step 1: Get Your Webhook URL
Your webhook URL is: http://your-server:8000/webhooks/tradingview

For local testing, use ngrok:
1. Install ngrok: brew install ngrok
2. Run: ngrok http 8000
3. Use the ngrok URL as your webhook

### Step 2: Create Pine Script Strategy
Copy one of the examples below into TradingView's Pine Editor.

### Step 3: Set Up Alert
1. Right-click on chart -> Add Alert
2. Set condition to your indicator/strategy
3. Enable "Webhook URL" and paste your URL
4. Set Message to the JSON format in the alert

### JSON Message Format
{
    "symbol": "{{ticker}}",
    "action": "BUY",
    "price": {{close}},
    "time": "{{time}}",
    "interval": "{{interval}}",
    "strategy": "Your Strategy Name",
    "message": "Signal description",
    "stop_loss": 145.00,
    "take_profit": 160.00,
    "confidence": 0.8
}
        """,
        "examples": PINE_SCRIPT_EXAMPLES,
    }

# Portfolio Tracker

A full-stack portfolio tracking application with AI-powered analysis and an autonomous multi-agent trading system.

## Features

### Portfolio Management
- **Dashboard**: Real-time portfolio value, P&L, and key metrics
- **Position Management**: Add, view, and delete positions
- **Allocation Chart**: Visual breakdown by asset type (stocks, ETFs, bonds, cash)
- **Performance Chart**: Historical portfolio value over time
- **Auto-refresh**: Prices update every 60 seconds

### AI Stock Analysis
- **Fundamental Analysis**: P/E, EPS, market cap, dividend yield
- **Technical Indicators**: RSI, moving averages, volume analysis
- **News Sentiment**: AI-powered news analysis with sentiment scoring
- **Watchlist**: Track stocks you're interested in

### Multi-Agent Trading System
Autonomous agents that work together to scan markets, execute trades, and learn from experience:

| Agent | Role |
|-------|------|
| **Orchestrator** | Central coordinator that routes messages between agents |
| **Scanner** | Monitors watchlist for trading signals using technical analysis |
| **Execution** | Executes trades via Interactive Brokers with position sizing |
| **Journal** | Tracks performance, identifies patterns, generates reports |

### TradingView Integration
- **Webhook Receiver**: Accept alerts from TradingView strategies
- **Pine Script Examples**: Ready-to-use indicator templates
- **Signal Processing**: Automatic routing to the agent system

### Interactive Brokers Integration
- **Account Sync**: Import positions directly from IBKR
- **Order Execution**: Place trades through the TWS API
- **Real-time Data**: Stream live prices (requires TWS/IB Gateway)

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React + TypeScript + Vite + Tailwind CSS + Recharts |
| **Backend** | Python FastAPI + SQLAlchemy |
| **Database** | SQLite |
| **Price Data** | Alpha Vantage API |
| **Broker** | Interactive Brokers (via ib_insync) |
| **Analysis** | TradingView technical analysis library |

## Project Structure

```
portfolio-tracker/
├── backend/
│   ├── main.py                 # FastAPI app entry point
│   ├── models.py               # SQLAlchemy models
│   ├── schemas.py              # Pydantic schemas
│   ├── database.py             # Database connection
│   ├── routers/
│   │   ├── positions.py        # Position CRUD
│   │   ├── portfolio.py        # Portfolio summary & history
│   │   ├── prices.py           # Price fetching
│   │   ├── transactions.py     # Transaction history
│   │   ├── ibkr.py             # Interactive Brokers integration
│   │   ├── analysis.py         # AI stock analysis
│   │   ├── data.py             # Data collection endpoints
│   │   ├── agents.py           # Agent system control
│   │   └── webhooks.py         # TradingView webhooks
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py             # Base agent class with memory
│   │   ├── orchestrator.py     # Central coordinator
│   │   ├── scanner.py          # Market scanner agent
│   │   ├── execution.py        # Trade execution agent
│   │   └── journal.py          # Trade journal agent
│   ├── services/
│   │   ├── prices.py           # Alpha Vantage price service
│   │   ├── portfolio.py        # Portfolio calculations
│   │   └── ibkr.py             # IBKR service wrapper
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── PositionTable.tsx
│   │   │   ├── AddPositionForm.tsx
│   │   │   ├── AllocationChart.tsx
│   │   │   ├── PerformanceChart.tsx
│   │   │   ├── IBKRConnect.tsx
│   │   │   ├── StockAnalysis.tsx
│   │   │   └── AgentDashboard.tsx
│   │   ├── services/
│   │   │   └── api.ts
│   │   └── types/
│   │       └── index.ts
│   ├── package.json
│   └── vite.config.ts
├── memory/                      # Agent memory persistence
├── start.sh                     # Quick start script
└── README.md
```

## Prerequisites

- Python 3.9+
- Node.js 18+
- Alpha Vantage API key (free tier: 25 requests/day)
- Interactive Brokers TWS or IB Gateway (optional, for trading)

## Setup

### 1. Clone the Repository

```bash
git clone https://github.com/Igkerdouki/portfolio-tracker.git
cd portfolio-tracker
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export ALPHA_VANTAGE_API_KEY=your_api_key
export TRADINGVIEW_WEBHOOK_SECRET=your_secret  # Optional

# Start the server
uvicorn main:app --reload
```

The API will be available at http://localhost:8000

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start the development server
npm run dev
```

The app will be available at http://localhost:5173

### Quick Start

```bash
# From project root
./start.sh
```

## API Endpoints

### Portfolio
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/positions` | List all positions with current prices |
| POST | `/positions` | Add a new position |
| PUT | `/positions/{id}` | Update a position |
| DELETE | `/positions/{id}` | Remove a position |
| GET | `/portfolio/summary` | Get portfolio summary with allocation |
| GET | `/portfolio/history` | Get historical performance data |

### Prices & Analysis
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/prices/{symbol}` | Get current price |
| GET | `/analysis/{symbol}` | Get AI analysis for a stock |
| GET | `/data/collect/{symbol}` | Collect fundamental data |

### Agents
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/agents/start` | Start the agent system |
| POST | `/agents/stop` | Stop the agent system |
| GET | `/agents/status` | Get status of all agents |
| GET | `/agents/messages` | Get inter-agent message log |
| POST | `/agents/scanner/watchlist` | Update scanner watchlist |
| GET | `/agents/scanner/signals` | Get recent trading signals |
| POST | `/agents/scanner/scan-now` | Trigger immediate scan |

### Webhooks
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/webhooks/tradingview` | Receive TradingView alerts |
| POST | `/webhooks/tradingview/test` | Test webhook endpoint |
| GET | `/webhooks/tradingview/pine-examples` | Get Pine Script examples |

### Interactive Brokers
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/ibkr/connect` | Connect to TWS/IB Gateway |
| GET | `/ibkr/status` | Get connection status |
| POST | `/ibkr/sync` | Sync positions from IBKR |

## TradingView Webhook Setup

1. Get your webhook URL: `https://your-domain.com/webhooks/tradingview`
2. For local testing, use ngrok: `ngrok http 8000`
3. Create an alert in TradingView with webhook enabled
4. Set the message to JSON format:

```json
{
  "symbol": "{{ticker}}",
  "action": "BUY",
  "price": {{close}},
  "time": "{{time}}",
  "interval": "{{interval}}",
  "strategy": "My Strategy",
  "message": "Signal description",
  "confidence": 0.8
}
```

## Agent Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     ORCHESTRATOR (CEO)                       │
│              Routes messages, manages priorities              │
└───────────┬─────────────────┬─────────────────┬─────────────┘
            │                 │                 │
            ▼                 ▼                 ▼
     ┌──────────┐      ┌──────────┐      ┌──────────┐
     │ SCANNER  │      │EXECUTION │      │ JOURNAL  │
     │          │ ───► │          │ ───► │          │
     │ Signals  │      │  Trades  │      │ Analysis │
     └──────────┘      └──────────┘      └──────────┘
            ▲
            │
     ┌──────────┐
     │TRADINGVIEW│
     │ Webhooks │
     └──────────┘
```

Agents communicate via typed messages with priority queues. Each agent maintains persistent memory to learn from past decisions.

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `ALPHA_VANTAGE_API_KEY` | API key for stock data | Yes |
| `TRADINGVIEW_WEBHOOK_SECRET` | Secret for webhook validation | No |
| `IBKR_HOST` | TWS/Gateway host (default: 127.0.0.1) | No |
| `IBKR_PORT` | TWS/Gateway port (default: 7497) | No |

## License

MIT

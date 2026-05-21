# Portfolio Tracker

A web-based portfolio tracker with real-time prices, performance charts, and allocation breakdown.

## Tech Stack

- **Frontend**: React + Vite + TypeScript + Tailwind CSS + Recharts
- **Backend**: Python FastAPI + SQLAlchemy
- **Database**: SQLite
- **Price Data**: Yahoo Finance (via yfinance library)

## Prerequisites

- Python 3.9+
- Node.js 18+
- npm or yarn

## Setup

### Backend

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn main:app --reload
```

The API will be available at http://localhost:8000

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start the development server
npm run dev
```

The app will be available at http://localhost:5173

## Features

- **Dashboard**: View total portfolio value, P&L, and key metrics
- **Position Management**: Add, view, and delete positions
- **Real-time Prices**: Prices auto-refresh every 60 seconds
- **Allocation Chart**: Visual breakdown by asset type
- **Performance Chart**: Historical portfolio value over time
- **Sortable Table**: Sort positions by symbol, value, P&L, etc.

## API Endpoints

- `GET /positions` - List all positions with current prices
- `POST /positions` - Add a new position
- `PUT /positions/{id}` - Update a position
- `DELETE /positions/{id}` - Remove a position
- `GET /portfolio/summary` - Get portfolio summary with allocation
- `GET /portfolio/history` - Get historical performance data
- `GET /prices/{symbol}` - Get current price for a symbol

## Project Structure

```
portfolio-tracker/
├── backend/
│   ├── main.py              # FastAPI app entry point
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic schemas
│   ├── database.py          # DB connection
│   ├── services/
│   │   ├── prices.py        # Price fetching service
│   │   └── portfolio.py     # Portfolio calculations
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── PositionTable.tsx
│   │   │   ├── AddPositionForm.tsx
│   │   │   ├── AllocationChart.tsx
│   │   │   └── PerformanceChart.tsx
│   │   ├── services/
│   │   │   └── api.ts
│   │   └── types/
│   │       └── index.ts
│   ├── package.json
│   └── vite.config.ts
└── README.md
```

"""
Portfolio Tracker API
Main FastAPI application entry point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine, Base
from routers import positions, portfolio, prices, transactions, ibkr, analysis, data, agents, webhooks, ml, sentiment, pairs, chat

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Portfolio Tracker API",
    description="API for tracking investment portfolio performance with AI analysis",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "Portfolio Tracker API", "version": "1.0.0"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


# Include routers
app.include_router(positions.router)
app.include_router(portfolio.router)
app.include_router(prices.router)
app.include_router(transactions.router)
app.include_router(ibkr.router)
app.include_router(analysis.router)
app.include_router(data.router)
app.include_router(agents.router)
app.include_router(webhooks.router)
app.include_router(ml.router)
app.include_router(sentiment.router)
app.include_router(pairs.router)
app.include_router(chat.router)

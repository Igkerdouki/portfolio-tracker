"""
Agent Chat Interface
Natural language interface for stock recommendations and analysis.
"""

import re
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import json

from services.stock_screener import stock_screener
from services.hedge_fund_metrics import HedgeFundMetrics
from services.enhanced_ml import EnhancedMLPredictor

try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False


class AgentChat:
    """
    Natural language chat interface for stock analysis and recommendations.
    """

    def __init__(self):
        self.conversation_history = []
        self.last_analysis = None
        self.context = {}

    def process_message(self, message: str) -> Dict:
        """
        Process a user message and return appropriate response.
        """
        message_lower = message.lower().strip()

        # Add to history
        self.conversation_history.append({
            "role": "user",
            "message": message,
            "timestamp": datetime.now().isoformat()
        })

        # Route to appropriate handler
        response = self._route_message(message_lower, message)

        # Add response to history
        self.conversation_history.append({
            "role": "agent",
            "message": response,
            "timestamp": datetime.now().isoformat()
        })

        return response

    def _route_message(self, message_lower: str, original: str) -> Dict:
        """Route message to appropriate handler."""

        # Stock recommendations
        if any(word in message_lower for word in ['recommend', 'suggest', 'best stocks', 'pick', 'what should i buy', 'good stocks']):
            return self._handle_recommendations(message_lower)

        # Short term / day trading
        if any(word in message_lower for word in ['short term', 'day trade', 'swing', 'quick', 'fast money', 'momentum']):
            return self._handle_short_term()

        # Long term / investment
        if any(word in message_lower for word in ['long term', 'invest', 'hold', 'dividend', 'retirement', 'growth']):
            return self._handle_long_term()

        # Specific stock analysis
        symbols = self._extract_symbols(original)
        if symbols:
            return self._handle_stock_analysis(symbols[0])

        # Market overview
        if any(word in message_lower for word in ['market', 'overview', 'how is the market', 'today']):
            return self._handle_market_overview()

        # Screener queries
        if any(word in message_lower for word in ['screen', 'filter', 'find', 'search']):
            return self._handle_screening(message_lower)

        # Metrics explanation
        if any(word in message_lower for word in ['what is', 'explain', 'mean', 'definition']):
            return self._handle_explanation(message_lower)

        # Compare stocks
        if 'compare' in message_lower or ' vs ' in message_lower or ' versus ' in message_lower:
            return self._handle_comparison(original)

        # Help
        if any(word in message_lower for word in ['help', 'what can you do', 'commands', 'how to']):
            return self._handle_help()

        # Default: try to understand intent
        return self._handle_default(message_lower)

    def _extract_symbols(self, text: str) -> List[str]:
        """Extract stock symbols from text."""
        # Look for $SYMBOL or uppercase words that might be symbols
        dollar_symbols = re.findall(r'\$([A-Z]{1,5})', text.upper())
        if dollar_symbols:
            return dollar_symbols

        # Look for common patterns
        words = text.upper().split()
        potential_symbols = [w for w in words if 1 <= len(w) <= 5 and w.isalpha()]

        # Validate against known symbols or try to fetch
        valid_symbols = []
        for sym in potential_symbols[:3]:  # Limit to 3
            try:
                if HAS_YFINANCE:
                    ticker = yf.Ticker(sym)
                    info = ticker.info
                    if info and 'regularMarketPrice' in info:
                        valid_symbols.append(sym)
            except:
                pass

        return valid_symbols

    def _handle_recommendations(self, message: str) -> Dict:
        """Handle stock recommendation requests."""
        # Determine strategy from message
        if any(word in message for word in ['tech', 'technology', 'software']):
            universe = 'tech'
        elif any(word in message for word in ['dividend', 'income', 'yield']):
            universe = 'dividend'
        elif any(word in message for word in ['growth', 'high growth']):
            universe = 'growth'
        elif any(word in message for word in ['value', 'cheap', 'undervalued']):
            universe = 'value'
        else:
            universe = 'sp500'

        # Determine strategy
        if any(word in message for word in ['momentum', 'trending', 'hot']):
            strategy = 'momentum'
        elif any(word in message for word in ['oversold', 'bounce', 'reversal']):
            strategy = 'reversal'
        else:
            strategy = 'momentum'

        results = stock_screener.screen_stocks(universe=universe, strategy=strategy, limit=5)

        if not results:
            return {
                "type": "recommendations",
                "message": "I couldn't find any stocks matching your criteria right now. Try being less specific or check back later.",
                "data": []
            }

        picks = []
        for r in results:
            picks.append({
                "symbol": r['symbol'],
                "price": f"${r['current_price']:.2f}",
                "score": r['score'],
                "trend": r['trend'],
                "return_1m": f"{r['metrics']['return_1m_pct']:.1f}%",
                "recommendation": r['recommendation']
            })

        return {
            "type": "recommendations",
            "message": f"Here are my top {len(picks)} {strategy} picks from the {universe} universe:",
            "data": picks,
            "strategy": strategy,
            "universe": universe
        }

    def _handle_short_term(self) -> Dict:
        """Handle short-term trading recommendations."""
        picks = stock_screener.get_short_term_picks(limit=5)

        momentum = picks.get('momentum_plays', [])[:3]
        reversal = picks.get('reversal_plays', [])[:3]

        return {
            "type": "short_term",
            "message": "Here are my short-term trading picks (1-4 week holding period):",
            "momentum_plays": [
                {
                    "symbol": s['symbol'],
                    "price": f"${s['current_price']:.2f}",
                    "score": s['score'],
                    "return_1w": f"{s['metrics']['return_1w_pct']:.1f}%",
                    "signal": s['signal_strength']
                }
                for s in momentum
            ],
            "reversal_plays": [
                {
                    "symbol": s['symbol'],
                    "price": f"${s['current_price']:.2f}",
                    "score": s['score'],
                    "rsi": f"{s['metrics']['rsi']:.0f}",
                    "signal": s['signal_strength']
                }
                for s in reversal
            ],
            "risk_warning": "Short-term trading carries higher risk. Use stop-losses and proper position sizing."
        }

    def _handle_long_term(self) -> Dict:
        """Handle long-term investment recommendations."""
        picks = stock_screener.get_long_term_picks(limit=5)

        return {
            "type": "long_term",
            "message": "Here are my long-term investment picks (6+ month holding period):",
            "growth_stocks": [
                {
                    "symbol": s['symbol'],
                    "price": f"${s['current_price']:.2f}",
                    "score": s['score'],
                    "return_1y": f"{s['metrics']['return_1y_pct']:.1f}%",
                    "trend": s['trend']
                }
                for s in picks.get('growth_stocks', [])[:3]
            ],
            "value_stocks": [
                {
                    "symbol": s['symbol'],
                    "price": f"${s['current_price']:.2f}",
                    "score": s['score'],
                    "vs_sma200": f"{(s['metrics']['price_vs_sma50'] - 1) * 100:.1f}%"
                }
                for s in picks.get('value_stocks', [])[:3]
            ],
            "dividend_stocks": [
                {
                    "symbol": s['symbol'],
                    "price": f"${s['current_price']:.2f}",
                    "score": s['score'],
                    "volatility": f"{s['metrics']['volatility_pct']:.1f}%"
                }
                for s in picks.get('dividend_stocks', [])[:3]
            ]
        }

    def _handle_stock_analysis(self, symbol: str) -> Dict:
        """Handle analysis of a specific stock."""
        try:
            predictor = EnhancedMLPredictor(symbol)
            predictor.fetch_and_prepare(period="2y")
            training_results = predictor.train()
            prediction = predictor.predict_next_day()

            # Quick price info
            data = predictor.data
            current_price = float(data['Close'].iloc[-1])
            prev_close = float(data['Close'].iloc[-2])
            change = (current_price - prev_close) / prev_close * 100

            # Technical levels
            sma_50 = float(data['Close'].rolling(50).mean().iloc[-1])
            sma_200 = float(data['Close'].rolling(200).mean().iloc[-1])

            return {
                "type": "stock_analysis",
                "symbol": symbol,
                "message": f"Here's my analysis of {symbol}:",
                "price_info": {
                    "current": f"${current_price:.2f}",
                    "change": f"{'+' if change > 0 else ''}{change:.2f}%",
                    "sma_50": f"${sma_50:.2f}",
                    "sma_200": f"${sma_200:.2f}",
                    "above_sma50": current_price > sma_50,
                    "above_sma200": current_price > sma_200
                },
                "ml_prediction": {
                    "direction": prediction['ensemble_prediction'],
                    "model_consensus": prediction['model_predictions'],
                    "recommendation": prediction['recommendation']
                },
                "model_accuracy": {
                    "random_forest": f"{training_results['model_results']['random_forest']['test_accuracy']:.1%}",
                    "gradient_boosting": f"{training_results['model_results']['gradient_boosting']['test_accuracy']:.1%}",
                    "ensemble": f"{training_results['model_results']['ensemble']['test_accuracy']:.1%}"
                },
                "top_features": training_results['feature_importance'][:5]
            }

        except Exception as e:
            return {
                "type": "error",
                "message": f"Sorry, I couldn't analyze {symbol}. Error: {str(e)}",
                "suggestion": "Make sure the symbol is valid and try again."
            }

    def _handle_market_overview(self) -> Dict:
        """Handle market overview request."""
        overview = stock_screener._get_market_overview()

        return {
            "type": "market_overview",
            "message": "Here's the current market overview:",
            "data": overview,
            "interpretation": self._interpret_market(overview)
        }

    def _interpret_market(self, overview: Dict) -> str:
        """Interpret market conditions."""
        if 'error' in overview:
            return "Unable to fetch market data."

        trend = overview.get('market_trend', 'NEUTRAL')
        vix = overview.get('vix', 20)
        env = overview.get('trading_environment', 'NEUTRAL')

        if env == 'RISK-ON':
            return "Market is in RISK-ON mode. Good conditions for growth stocks and momentum plays."
        elif env == 'RISK-OFF':
            return "Market is in RISK-OFF mode. Consider defensive positions, value stocks, or cash."
        else:
            return f"Market is {trend}. VIX at {vix:.1f}. Mixed conditions - be selective."

    def _handle_screening(self, message: str) -> Dict:
        """Handle stock screening requests."""
        # Parse screening criteria from message
        strategy = 'momentum'
        if 'value' in message:
            strategy = 'value'
        elif 'growth' in message:
            strategy = 'growth'
        elif 'dividend' in message:
            strategy = 'dividend'
        elif 'volatile' in message or 'volatility' in message:
            strategy = 'volatility'

        results = stock_screener.screen_stocks(strategy=strategy, limit=10)

        return {
            "type": "screening",
            "message": f"Found {len(results)} stocks matching '{strategy}' strategy:",
            "results": [
                {
                    "symbol": r['symbol'],
                    "score": r['score'],
                    "price": f"${r['current_price']:.2f}",
                    "recommendation": r['recommendation']
                }
                for r in results
            ]
        }

    def _handle_comparison(self, message: str) -> Dict:
        """Handle stock comparison requests."""
        symbols = self._extract_symbols(message)

        if len(symbols) < 2:
            # Try to extract from vs/versus pattern
            parts = re.split(r'\s+vs\.?\s+|\s+versus\s+', message, flags=re.IGNORECASE)
            for part in parts:
                syms = self._extract_symbols(part)
                symbols.extend(syms)

        symbols = list(set(symbols))[:2]  # Limit to 2

        if len(symbols) < 2:
            return {
                "type": "error",
                "message": "Please specify two stock symbols to compare (e.g., 'compare AAPL vs MSFT')"
            }

        comparisons = []
        for sym in symbols:
            try:
                predictor = EnhancedMLPredictor(sym)
                predictor.fetch_and_prepare(period="1y")
                predictor.train()
                pred = predictor.predict_next_day()
                data = predictor.data

                return_1y = (data['Close'].iloc[-1] / data['Close'].iloc[0] - 1) * 100
                volatility = data['Close'].pct_change().std() * np.sqrt(252) * 100

                comparisons.append({
                    "symbol": sym,
                    "price": f"${float(data['Close'].iloc[-1]):.2f}",
                    "return_1y": f"{return_1y:.1f}%",
                    "volatility": f"{volatility:.1f}%",
                    "prediction": pred['ensemble_prediction'],
                    "recommendation": pred['recommendation']
                })
            except Exception as e:
                comparisons.append({
                    "symbol": sym,
                    "error": str(e)
                })

        return {
            "type": "comparison",
            "message": f"Comparison of {symbols[0]} vs {symbols[1]}:",
            "stocks": comparisons
        }

    def _handle_explanation(self, message: str) -> Dict:
        """Handle metric/term explanations."""
        explanations = {
            "sharpe": {
                "term": "Sharpe Ratio",
                "explanation": "Measures risk-adjusted return. Higher is better. Above 1 is good, above 2 is excellent. It tells you how much return you get per unit of risk.",
                "formula": "(Return - Risk-free Rate) / Volatility"
            },
            "sortino": {
                "term": "Sortino Ratio",
                "explanation": "Like Sharpe but only considers downside risk. Better for asymmetric returns. Higher is better.",
                "formula": "(Return - Risk-free Rate) / Downside Deviation"
            },
            "drawdown": {
                "term": "Maximum Drawdown",
                "explanation": "The largest peak-to-trough decline. Shows worst-case loss. -20% means you lost 20% from the highest point.",
                "formula": "(Trough Value - Peak Value) / Peak Value"
            },
            "var": {
                "term": "Value at Risk (VaR)",
                "explanation": "The maximum expected loss at a confidence level. VaR 95% of -2% means there's a 5% chance of losing more than 2% in a day.",
                "formula": "Percentile of return distribution"
            },
            "alpha": {
                "term": "Alpha",
                "explanation": "Excess return above the benchmark (like S&P 500). Positive alpha means you're beating the market.",
                "formula": "Strategy Return - (Risk-free + Beta × Market Return)"
            },
            "beta": {
                "term": "Beta",
                "explanation": "Measures volatility relative to market. Beta of 1.5 means 50% more volatile than S&P 500. Beta < 1 is defensive.",
                "formula": "Covariance(Stock, Market) / Variance(Market)"
            },
            "calmar": {
                "term": "Calmar Ratio",
                "explanation": "Return divided by max drawdown. Shows return per unit of pain. Higher is better.",
                "formula": "Annual Return / |Max Drawdown|"
            },
            "rsi": {
                "term": "RSI (Relative Strength Index)",
                "explanation": "Momentum oscillator from 0-100. Above 70 is overbought (might fall), below 30 is oversold (might rise).",
                "formula": "100 - (100 / (1 + Average Gain / Average Loss))"
            },
            "macd": {
                "term": "MACD",
                "explanation": "Trend-following momentum indicator. Buy when MACD crosses above signal line, sell when it crosses below.",
                "formula": "12-day EMA - 26-day EMA"
            },
            "kelly": {
                "term": "Kelly Criterion",
                "explanation": "Optimal bet size to maximize growth. Tells you what % of capital to risk. 20% Kelly means bet 20% of portfolio.",
                "formula": "Win Rate - (1 - Win Rate) / Payoff Ratio"
            }
        }

        for key, value in explanations.items():
            if key in message:
                return {
                    "type": "explanation",
                    "term": value['term'],
                    "explanation": value['explanation'],
                    "formula": value['formula']
                }

        return {
            "type": "explanation",
            "message": "I can explain: Sharpe Ratio, Sortino Ratio, Drawdown, VaR, Alpha, Beta, Calmar Ratio, RSI, MACD, Kelly Criterion. Which would you like to know about?"
        }

    def _handle_help(self) -> Dict:
        """Handle help requests."""
        return {
            "type": "help",
            "message": "I'm your AI stock analyst! Here's what I can do:",
            "capabilities": [
                {
                    "command": "Recommend stocks",
                    "examples": ["Give me stock recommendations", "Best tech stocks", "Suggest dividend stocks"]
                },
                {
                    "command": "Short-term picks",
                    "examples": ["Short term trades", "Momentum plays", "Swing trade ideas"]
                },
                {
                    "command": "Long-term picks",
                    "examples": ["Long term investments", "Growth stocks", "Value stocks"]
                },
                {
                    "command": "Analyze stock",
                    "examples": ["Analyze AAPL", "What about TSLA?", "Tell me about NVDA"]
                },
                {
                    "command": "Compare stocks",
                    "examples": ["Compare AAPL vs MSFT", "GOOGL versus META"]
                },
                {
                    "command": "Market overview",
                    "examples": ["How is the market?", "Market overview", "Today's market"]
                },
                {
                    "command": "Screen stocks",
                    "examples": ["Find growth stocks", "Screen for value", "High volatility stocks"]
                },
                {
                    "command": "Explain terms",
                    "examples": ["What is Sharpe ratio?", "Explain RSI", "What does alpha mean?"]
                }
            ]
        }

    def _handle_default(self, message: str) -> Dict:
        """Handle unrecognized messages."""
        return {
            "type": "default",
            "message": "I'm not sure what you're asking. Try asking for stock recommendations, analysis of a specific stock (like 'analyze AAPL'), or type 'help' to see what I can do!",
            "suggestions": [
                "Give me stock recommendations",
                "Analyze TSLA",
                "Short term trading ideas",
                "What is Sharpe ratio?",
                "Compare AAPL vs MSFT"
            ]
        }

    def get_history(self) -> List[Dict]:
        """Get conversation history."""
        return self.conversation_history

    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []


# Global instance
agent_chat = AgentChat()

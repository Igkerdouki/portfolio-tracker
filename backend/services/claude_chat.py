"""
Claude-Powered Investment Chat
Real conversational AI using Claude API for intelligent investment advice.
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional
import httpx

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False


class ClaudeInvestmentAdvisor:
    """
    A Claude-powered investment advisor that provides friendly,
    educational, and data-driven advice for all experience levels.
    """

    SYSTEM_PROMPT = """You are a friendly and knowledgeable investment advisor named "Yiayia's Alpha" (like a wise Greek grandmother who knows finance!). Your personality:

**Who You Are:**
- Warm, approachable, and encouraging - like a smart friend who happens to know a lot about investing
- You explain complex financial concepts in simple terms anyone can understand
- You use real data and numbers to support your advice, but present them in a digestible way
- You're honest about risks and never overpromise

**How You Communicate:**
- Use conversational, friendly language (but still professional)
- Break down jargon into simple explanations
- Use analogies and examples from everyday life
- Add a touch of warmth and encouragement
- Use emojis sparingly but appropriately to be friendly 😊

**What You Do:**
- Analyze stocks using real market data (provided in context)
- Explain WHY something is a good or bad investment, not just what to do
- Educate users about investing concepts as you go
- Consider the user's apparent experience level and adjust your explanations
- Always mention both opportunities AND risks
- Never give guarantees - investing always involves risk

**Important Rules:**
- If you don't have data, say so honestly
- Remind users this is educational, not financial advice
- Be encouraging but realistic
- Celebrate learning, not just profits
- Help users understand metrics like P/E ratio, Sharpe ratio, etc. in simple terms

**Example Style:**
Instead of: "The RSI is 72, indicating overbought conditions."
Say: "The RSI is at 72, which is like a 'popularity meter' for stocks - when it's this high (above 70), it often means a lot of people have already bought in, so the price might take a breather soon. Think of it like a party that's getting crowded! 🎉"

Remember: You're helping real people with their hard-earned money. Be helpful, honest, and kind."""

    def __init__(self):
        self.api_key = os.environ.get('ANTHROPIC_API_KEY', '')
        self.conversation_history = []
        self.client = None

        if HAS_ANTHROPIC and self.api_key:
            self.client = anthropic.Anthropic(api_key=self.api_key)

    def get_stock_context(self, symbols: List[str]) -> str:
        """Fetch real-time stock data to provide context for Claude."""
        if not HAS_YFINANCE:
            return "Stock data unavailable."

        context_parts = []

        for symbol in symbols[:3]:  # Limit to 3 stocks
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                hist = ticker.history(period="3mo")

                if len(hist) == 0:
                    continue

                current_price = hist['Close'].iloc[-1]
                price_1m_ago = hist['Close'].iloc[-21] if len(hist) > 21 else hist['Close'].iloc[0]
                price_3m_ago = hist['Close'].iloc[0]

                return_1m = (current_price / price_1m_ago - 1) * 100
                return_3m = (current_price / price_3m_ago - 1) * 100

                volatility = hist['Close'].pct_change().std() * (252 ** 0.5) * 100

                # RSI
                delta = hist['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs.iloc[-1])) if loss.iloc[-1] != 0 else 50

                # 50-day MA
                sma_50 = hist['Close'].rolling(50).mean().iloc[-1] if len(hist) >= 50 else current_price

                context_parts.append(f"""
**{symbol} Real-Time Data:**
- Current Price: ${current_price:.2f}
- 1-Month Return: {return_1m:+.1f}%
- 3-Month Return: {return_3m:+.1f}%
- Annual Volatility: {volatility:.1f}%
- RSI (14-day): {rsi:.0f}
- vs 50-day MA: {((current_price/sma_50)-1)*100:+.1f}%
- Company: {info.get('longName', symbol)}
- Sector: {info.get('sector', 'N/A')}
- P/E Ratio: {info.get('trailingPE', 'N/A')}
- Market Cap: ${info.get('marketCap', 0)/1e9:.1f}B
- 52-Week High: ${info.get('fiftyTwoWeekHigh', 0):.2f}
- 52-Week Low: ${info.get('fiftyTwoWeekLow', 0):.2f}
""")
            except Exception as e:
                context_parts.append(f"Could not fetch data for {symbol}: {str(e)}")

        return "\n".join(context_parts) if context_parts else "No stock data available."

    def extract_symbols(self, message: str) -> List[str]:
        """Extract potential stock symbols from message."""
        import re

        # Look for $SYMBOL pattern
        dollar_symbols = re.findall(r'\$([A-Z]{1,5})', message.upper())
        if dollar_symbols:
            return dollar_symbols

        # Common stock names to symbol mapping
        name_to_symbol = {
            'apple': 'AAPL', 'microsoft': 'MSFT', 'google': 'GOOGL', 'amazon': 'AMZN',
            'tesla': 'TSLA', 'nvidia': 'NVDA', 'meta': 'META', 'facebook': 'META',
            'netflix': 'NFLX', 'visa': 'V', 'mastercard': 'MA', 'jpmorgan': 'JPM',
            'disney': 'DIS', 'nike': 'NKE', 'coca-cola': 'KO', 'coke': 'KO',
            'pepsi': 'PEP', 'walmart': 'WMT', 'costco': 'COST', 'wise': 'WISE.L',
        }

        message_lower = message.lower()
        found = []
        for name, symbol in name_to_symbol.items():
            if name in message_lower:
                found.append(symbol)

        # Look for uppercase words that might be symbols
        if not found:
            words = message.upper().split()
            for word in words:
                clean = re.sub(r'[^A-Z]', '', word)
                if 1 <= len(clean) <= 5:
                    found.append(clean)

        return found[:3]  # Limit to 3

    async def chat(self, user_message: str) -> Dict:
        """
        Have a conversation with the Claude-powered advisor.
        """
        # Extract any stock symbols mentioned
        symbols = self.extract_symbols(user_message)

        # Get real stock data for context
        stock_context = ""
        if symbols:
            stock_context = self.get_stock_context(symbols)

        # Build the message with context
        enhanced_message = user_message
        if stock_context and stock_context != "No stock data available.":
            enhanced_message = f"""{user_message}

[REAL-TIME MARKET DATA FOR YOUR REFERENCE]
{stock_context}

Please use this real data in your response to give accurate, data-driven advice."""

        # Add to conversation history
        self.conversation_history.append({
            "role": "user",
            "content": enhanced_message
        })

        # If no API key, use a helpful fallback
        if not self.client:
            return self._fallback_response(user_message, symbols, stock_context)

        try:
            # Call Claude API
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1500,
                system=self.SYSTEM_PROMPT,
                messages=self.conversation_history[-10:]  # Keep last 10 messages for context
            )

            assistant_message = response.content[0].text

            # Add to history
            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_message
            })

            return {
                "type": "claude_response",
                "message": assistant_message,
                "symbols_analyzed": symbols,
                "has_real_data": bool(stock_context and stock_context != "No stock data available."),
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            return {
                "type": "error",
                "message": f"I'm having trouble connecting right now. Error: {str(e)}",
                "fallback": self._fallback_response(user_message, symbols, stock_context)
            }

    def _fallback_response(self, message: str, symbols: List[str], stock_context: str) -> Dict:
        """Provide helpful response when API is unavailable."""

        message_lower = message.lower()

        # Check if it's a greeting
        greetings = ['hi', 'hello', 'hey', 'good morning', 'good evening']
        if any(g in message_lower for g in greetings):
            return {
                "type": "greeting",
                "message": """Hey there! Welcome to your investment advisor.

I'm here to help you understand investing and make smarter decisions with your money. Whether you're a complete beginner or experienced trader, I've got you covered.

**What I can help with:**
- Analyze any stock (just mention the name or symbol)
- Explain investing terms in simple English
- Discuss investment strategies
- Help you think through buy/sell decisions

**Try asking:**
- "Tell me about Tesla"
- "What does P/E ratio mean?"
- "Is Apple a good long-term investment?"
- "Explain Sharpe ratio simply"

What would you like to explore?""",
                "timestamp": datetime.now().isoformat()
            }

        # Financial term explanations
        term_explanations = {
            'p/e': """**P/E Ratio (Price-to-Earnings)**

Think of it as "how many years of profits you're paying for."

**Example:** If a stock has P/E of 20, you're paying $20 for every $1 of annual profit.

**What's good?**
- Under 15: Often considered cheap/value
- 15-25: Average range
- Over 25: Expensive, but growth stocks often have high P/E

**Watch out:** A low P/E isn't always good - the company might be struggling. High P/E isn't always bad - fast-growing companies deserve higher valuations.

**Compare within the same industry** - tech stocks normally have higher P/E than banks.""",

            'sharpe': """**Sharpe Ratio**

Measures how much return you get for the risk you take. Named after Nobel laureate William Sharpe.

**Simple version:** "Reward per unit of stress"

**What's good?**
- Under 1: Not great risk-adjusted returns
- 1-2: Good
- 2-3: Very good
- Over 3: Excellent (rare to sustain)

**Why it matters:** A 20% return sounds great, but not if you had to stomach 50% swings. Sharpe ratio accounts for that volatility.

**Formula (simplified):** (Your Return - Risk-Free Rate) / Your Volatility""",

            'rsi': """**RSI (Relative Strength Index)**

A momentum indicator from 0-100 that shows if a stock is "overbought" or "oversold."

**How to read it:**
- Above 70: Overbought - many buyers already in, price might cool off
- Below 30: Oversold - heavy selling, might bounce back
- 30-70: Neutral zone

**Important:** RSI doesn't predict the future! A stock can stay overbought for months during strong trends.

**Best use:** Combine with other indicators. Don't buy just because RSI is low, or sell just because it's high.""",

            'macd': """**MACD (Moving Average Convergence Divergence)**

A trend-following indicator that shows momentum direction.

**Three parts:**
1. MACD Line (fast) - 12-day EMA minus 26-day EMA
2. Signal Line (slow) - 9-day EMA of MACD
3. Histogram - difference between the two

**Trading signals:**
- MACD crosses ABOVE signal = bullish
- MACD crosses BELOW signal = bearish
- Histogram getting bigger = momentum increasing

**Best for:** Confirming trends, not predicting reversals.""",

            'dividend': """**Dividends**

Cash payments companies make to shareholders, usually quarterly.

**Key terms:**
- **Dividend Yield:** Annual dividend / Stock price (e.g., 3% yield)
- **Payout Ratio:** % of profits paid as dividends
- **Ex-Dividend Date:** Must own before this date to get dividend

**Good dividend stocks typically have:**
- Long history of payments
- Payout ratio under 70%
- Stable cash flow business

**Watch out:** Very high yields (8%+) might mean the stock price dropped or dividend could be cut.""",

            'market cap': """**Market Cap (Market Capitalization)**

Total value of all a company's shares. Price per share × Number of shares.

**Size categories:**
- **Large Cap:** Over $10 billion (Apple, Microsoft, etc.)
- **Mid Cap:** $2-10 billion
- **Small Cap:** $300 million - $2 billion
- **Micro Cap:** Under $300 million

**Why it matters:**
- Large caps: More stable, less growth potential
- Small caps: More volatile, higher growth potential
- Index funds often track by market cap"""
        }

        # Check for term explanations
        for term, explanation in term_explanations.items():
            if term in message_lower or term.replace('/', '') in message_lower.replace(' ', ''):
                return {
                    "type": "explanation",
                    "message": explanation,
                    "timestamp": datetime.now().isoformat()
                }

        # If asking about a stock
        if symbols and stock_context:
            symbol = symbols[0]
            return {
                "type": "stock_analysis",
                "message": f"""Here's my analysis of **{symbol}**:

{stock_context}

**Quick Take:**

1. **Recent Performance**: The monthly/quarterly returns show recent momentum direction
2. **RSI Level**: Above 70 = overbought (might cool off), Below 30 = oversold (might bounce)
3. **vs 50-day MA**: Above = uptrend, Below = downtrend

**What to consider:**
- What's your timeframe - long term (years) or short term (months)?
- How much volatility can you handle?
- Does this fit your overall portfolio?

**Key questions to research:**
- What's driving recent price movement?
- How does it compare to competitors?
- What's the growth outlook?

*Remember: This is educational analysis, not financial advice. Always do your own research.*""",
                "symbols": symbols,
                "has_real_data": True,
                "timestamp": datetime.now().isoformat()
            }

        # Recommendation requests
        if any(word in message_lower for word in ['recommend', 'suggest', 'should i buy', 'good stock', 'best stock']):
            return {
                "type": "recommendation",
                "message": """**How to Find Good Stocks**

Rather than give you specific picks (which depends on YOUR situation), here's a framework:

**For Beginners:**
- Start with broad ETFs like SPY (S&P 500) or VTI (Total Market)
- Less risk, instant diversification
- Warren Buffett recommends this for most people

**If You Want Individual Stocks:**

1. **Blue Chips** (Lower risk): Apple, Microsoft, Johnson & Johnson
   - Stable, profitable, dividend payers

2. **Growth** (Higher risk/reward): Companies growing revenue 20%+ yearly
   - More volatile but higher potential

3. **Value** (Patience required): Underpriced relative to earnings
   - Requires more research

**My Advice:**
- Don't put all eggs in one basket
- Only invest what you can leave for 5+ years
- Learn basics before picking individual stocks

What's your experience level and goal? I can give more specific guidance.""",
                "timestamp": datetime.now().isoformat()
            }

        # Long term vs short term
        if 'long term' in message_lower or 'short term' in message_lower:
            return {
                "type": "educational",
                "message": """**Long Term vs Short Term Investing**

**Long Term (1+ years):**
- Focus on fundamentals, not daily price moves
- Benefits from compound growth
- Lower taxes (long-term capital gains)
- Less stressful, fewer decisions
- Best for: retirement, wealth building

**Short Term (days to months):**
- More about technical analysis and momentum
- Higher taxes (short-term = income tax rate)
- Requires more time and attention
- Higher risk of loss
- Best for: active traders with time to monitor

**The Data Says:**
Studies show most day traders lose money. Long-term buy-and-hold beats active trading for most people.

**My Take:**
Unless you have significant time to dedicate, long-term investing in quality companies or ETFs is the way to go.

What's your situation?""",
                "timestamp": datetime.now().isoformat()
            }

        # General investing question
        return {
            "type": "educational",
            "message": """Good question! To give you the best answer, could you tell me:

1. **What specifically** are you trying to understand or decide?
2. **Your experience** - new to investing or have some background?
3. **Any specific stocks** you're looking at?

**Some things I can help with:**
- Explain any investing term (P/E, RSI, Sharpe ratio, etc.)
- Analyze specific stocks with real data
- Discuss strategies (long-term, dividends, growth, etc.)
- Compare investment options

Just ask! For example:
- "What does P/E ratio mean?"
- "Analyze Tesla for me"
- "Should I invest in ETFs or individual stocks?"
- "Explain dividends"

What's on your mind?""",
            "timestamp": datetime.now().isoformat()
        }

    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []

    def get_history(self) -> List[Dict]:
        """Get conversation history."""
        return self.conversation_history


# Global instance
claude_advisor = ClaudeInvestmentAdvisor()

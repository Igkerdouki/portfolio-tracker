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

        # Check if it's a greeting
        greetings = ['hi', 'hello', 'hey', 'good morning', 'good evening']
        if any(g in message.lower() for g in greetings):
            return {
                "type": "greeting",
                "message": """Hey there! 👋 Welcome to Yiayia's Alpha - your friendly investment buddy!

I'm here to help you understand investing and make smarter decisions with your money. Whether you're a complete beginner or just want a second opinion, I've got your back!

**Here's what I can help you with:**
- 📊 Analyze any stock (just mention the name or symbol)
- 📚 Explain investing terms in simple English
- 💡 Discuss investment strategies
- ⚖️ Help you think through buy/sell decisions

**Try asking me things like:**
- "Tell me about Tesla - should I invest?"
- "What does P/E ratio mean?"
- "Is Apple a good long-term investment?"
- "Explain what a Sharpe ratio is like I'm 5"

What would you like to explore today? 😊""",
                "timestamp": datetime.now().isoformat()
            }

        # If asking about a stock
        if symbols and stock_context:
            symbol = symbols[0]
            return {
                "type": "stock_analysis",
                "message": f"""Great question about {symbol}! Let me break this down for you. 📊

{stock_context}

**My Quick Take:**
Based on this data, here's what stands out:

1. **Recent Performance**: Look at those monthly returns - they tell you the recent momentum
2. **RSI Level**: If it's above 70, the stock might be "overbought" (lots of buyers recently). Below 30 means "oversold" (lots of sellers)
3. **vs 50-day MA**: If the price is above this average, it's in an uptrend. Below = downtrend

**What This Means For You:**
To give you truly personalized advice, I'd love to know:
- Are you looking to invest for the long term (years) or short term (weeks/months)?
- How much risk are you comfortable with?
- Do you already own this stock or thinking of buying?

Tell me more about your situation and I'll give you a more specific take! 💬

*Remember: I'm here to educate, not give financial advice. Always do your own research! 📚*""",
                "symbols": symbols,
                "timestamp": datetime.now().isoformat()
            }

        # General investing question
        return {
            "type": "educational",
            "message": """That's a great question! 🤔

I want to give you a thoughtful, personalized answer. Could you tell me a bit more about:

1. **Your experience level** - Are you new to investing or have some experience?
2. **Your goal** - Growing wealth long-term? Generating income? Short-term gains?
3. **Specific stocks or topics** - Any particular companies or concepts you're curious about?

The more context you give me, the better I can help!

For example, you could ask:
- "I'm new to investing and have $1000 to start - where should I begin?"
- "Analyze AAPL for me - I'm thinking of buying"
- "What's the difference between stocks and ETFs?"

I'm all ears! 👂""",
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

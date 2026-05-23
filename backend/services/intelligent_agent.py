"""
Intelligent Finance Agent
A sophisticated AI agent powered by LLMs (Groq/Anthropic) with memory, learning, and real data integration.
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

# Try Groq first (free tier available)
try:
    from groq import Groq
    HAS_GROQ = True
except ImportError:
    HAS_GROQ = False

# Anthropic as fallback
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


class AgentMemory:
    """Persistent memory for the agent - remembers conversations and learns."""

    def __init__(self, memory_file: str = "agent_memory.json"):
        self.memory_path = Path(__file__).parent.parent / "data" / memory_file
        self.memory_path.parent.mkdir(exist_ok=True)
        self.memory = self._load_memory()

    def _load_memory(self) -> Dict:
        if self.memory_path.exists():
            try:
                with open(self.memory_path, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {
            "conversations": [],
            "user_preferences": {},
            "learned_corrections": [],
            "frequently_asked": {},
            "user_portfolio_context": {}
        }

    def save(self):
        with open(self.memory_path, 'w') as f:
            json.dump(self.memory, f, indent=2, default=str)

    def add_conversation(self, user_msg: str, agent_response: str):
        self.memory["conversations"].append({
            "timestamp": datetime.now().isoformat(),
            "user": user_msg,
            "agent": agent_response[:500]  # Truncate for storage
        })
        # Keep last 100 conversations
        self.memory["conversations"] = self.memory["conversations"][-100:]
        self._update_frequently_asked(user_msg)
        self.save()

    def _update_frequently_asked(self, question: str):
        # Track common question patterns
        key_words = ['what is', 'how to', 'should i', 'explain', 'compare', 'analyze']
        for kw in key_words:
            if kw in question.lower():
                self.memory["frequently_asked"][kw] = self.memory["frequently_asked"].get(kw, 0) + 1

    def add_correction(self, original: str, correction: str):
        """Store corrections to improve future responses."""
        self.memory["learned_corrections"].append({
            "timestamp": datetime.now().isoformat(),
            "original": original,
            "correction": correction
        })
        self.save()

    def set_user_preference(self, key: str, value: Any):
        self.memory["user_preferences"][key] = value
        self.save()

    def get_user_preference(self, key: str, default: Any = None) -> Any:
        return self.memory["user_preferences"].get(key, default)

    def get_context_summary(self) -> str:
        """Get a summary of learned context for the agent."""
        prefs = self.memory["user_preferences"]
        recent = self.memory["conversations"][-5:] if self.memory["conversations"] else []

        summary_parts = []

        if prefs:
            summary_parts.append(f"User preferences: {json.dumps(prefs)}")

        if recent:
            summary_parts.append("Recent conversation topics: " +
                ", ".join([c["user"][:50] for c in recent]))

        return "\n".join(summary_parts) if summary_parts else "No prior context."


class IntelligentFinanceAgent:
    """
    A sophisticated AI finance agent powered by Claude.
    Features:
    - Real-time market data integration
    - Persistent memory and learning
    - Context-aware responses
    - Comparative analysis capabilities
    """

    SYSTEM_PROMPT = """You are an expert financial advisor AI agent. You provide intelligent, nuanced advice on all financial topics.

**Your Capabilities:**
- Compare investment vehicles (stocks, bonds, ETFs, treasury bills, etc.)
- Analyze specific stocks with real market data
- Explain complex financial concepts simply
- Provide personalized recommendations based on user context
- Discuss macroeconomics, market trends, and investment strategies

**Your Approach:**
1. Always use real data when available (provided in context)
2. Give balanced views - pros AND cons
3. Explain your reasoning, don't just give answers
4. Ask clarifying questions when needed
5. Remember what the user has told you and adapt
6. Be direct but friendly

**Important Guidelines:**
- When comparing options (bonds vs stocks, etc.), give specific numbers and scenarios
- Use concrete examples with real calculations
- Acknowledge uncertainty - markets are unpredictable
- Tailor advice to the user's stated risk tolerance and goals
- Always mention this is educational, not personalized financial advice

**For Questions Like "Should I buy X or Y?":**
1. Explain what each option IS and how it works
2. Compare: risk, potential returns, liquidity, tax implications
3. Discuss who each option is best for
4. Ask about their specific situation if unclear
5. Give a balanced recommendation with reasoning

You have access to real-time market data. Use it to make your answers specific and data-driven."""

    def __init__(self):
        self.groq_key = os.environ.get('GROQ_API_KEY', '')
        self.anthropic_key = os.environ.get('ANTHROPIC_API_KEY', '')
        self.groq_client = None
        self.anthropic_client = None
        self.memory = AgentMemory()
        self.conversation_history = []
        self.provider = None  # 'groq', 'anthropic', or None

        # Try Groq first (free tier)
        if HAS_GROQ and self.groq_key:
            self.groq_client = Groq(api_key=self.groq_key)
            self.provider = 'groq'
        # Fall back to Anthropic
        elif HAS_ANTHROPIC and self.anthropic_key:
            self.anthropic_client = anthropic.Anthropic(api_key=self.anthropic_key)
            self.provider = 'anthropic'

    @property
    def is_intelligent(self) -> bool:
        """Returns True if an LLM API is available."""
        return self.provider is not None

    @property
    def provider_name(self) -> str:
        """Returns the name of the active provider."""
        if self.provider == 'groq':
            return 'Groq (Llama 3)'
        elif self.provider == 'anthropic':
            return 'Claude'
        return 'Fallback Mode'

    def get_market_data(self, symbols: List[str]) -> str:
        """Fetch comprehensive market data for context."""
        if not HAS_YFINANCE or not symbols:
            return ""

        data_parts = []

        for symbol in symbols[:5]:
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                hist = ticker.history(period="6mo")

                if len(hist) == 0:
                    continue

                current = hist['Close'].iloc[-1]
                prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else current

                # Calculate metrics
                daily_change = (current - prev_close) / prev_close * 100
                week_return = (current / hist['Close'].iloc[-5] - 1) * 100 if len(hist) > 5 else 0
                month_return = (current / hist['Close'].iloc[-21] - 1) * 100 if len(hist) > 21 else 0
                ytd_return = (current / hist['Close'].iloc[0] - 1) * 100
                volatility = hist['Close'].pct_change().std() * (252 ** 0.5) * 100

                # RSI
                delta = hist['Close'].diff()
                gain = delta.where(delta > 0, 0).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs.iloc[-1])) if loss.iloc[-1] != 0 else 50

                # Moving averages
                sma50 = hist['Close'].rolling(50).mean().iloc[-1] if len(hist) >= 50 else current
                sma200 = hist['Close'].rolling(200).mean().iloc[-1] if len(hist) >= 200 else current

                data_parts.append(f"""
**{symbol} ({info.get('shortName', symbol)})**
- Price: ${current:.2f} ({daily_change:+.2f}% today)
- 1 Week: {week_return:+.1f}% | 1 Month: {month_return:+.1f}% | YTD: {ytd_return:+.1f}%
- Volatility: {volatility:.1f}% annualized
- RSI(14): {rsi:.0f} {'(overbought)' if rsi > 70 else '(oversold)' if rsi < 30 else ''}
- vs 50-day MA: {((current/sma50)-1)*100:+.1f}% | vs 200-day MA: {((current/sma200)-1)*100:+.1f}%
- P/E: {info.get('trailingPE', 'N/A')} | Market Cap: ${info.get('marketCap', 0)/1e9:.1f}B
- 52-Week Range: ${info.get('fiftyTwoWeekLow', 0):.2f} - ${info.get('fiftyTwoWeekHigh', 0):.2f}
- Sector: {info.get('sector', 'N/A')}
""")
            except Exception as e:
                continue

        return "\n".join(data_parts) if data_parts else ""

    def get_treasury_rates(self) -> str:
        """Get current treasury rates."""
        try:
            # Treasury ETF proxies
            tickers = {
                "^IRX": "3-Month T-Bill",
                "^FVX": "5-Year Treasury",
                "^TNX": "10-Year Treasury",
                "^TYX": "30-Year Treasury"
            }

            rates = []
            for symbol, name in tickers.items():
                try:
                    data = yf.download(symbol, period="5d", progress=False)
                    if len(data) > 0:
                        rate = data['Close'].iloc[-1]
                        rates.append(f"- {name}: {rate:.2f}%")
                except:
                    continue

            if rates:
                return "**Current Treasury Rates:**\n" + "\n".join(rates)
        except:
            pass
        return ""

    def extract_symbols(self, text: str) -> List[str]:
        """Extract stock symbols from text."""
        import re

        # Common name to symbol mapping
        name_map = {
            'apple': 'AAPL', 'microsoft': 'MSFT', 'google': 'GOOGL', 'amazon': 'AMZN',
            'tesla': 'TSLA', 'nvidia': 'NVDA', 'meta': 'META', 'netflix': 'NFLX',
            'visa': 'V', 'mastercard': 'MA', 'jpmorgan': 'JPM', 'disney': 'DIS',
            'coca-cola': 'KO', 'coke': 'KO', 'pepsi': 'PEP', 'walmart': 'WMT',
            'spy': 'SPY', 'qqq': 'QQQ', 'voo': 'VOO', 'vti': 'VTI',
        }

        symbols = []
        text_lower = text.lower()

        # Check for $SYMBOL pattern
        dollar_symbols = re.findall(r'\$([A-Z]{1,5})', text.upper())
        symbols.extend(dollar_symbols)

        # Check for company names
        for name, symbol in name_map.items():
            if name in text_lower:
                symbols.append(symbol)

        # Check for standalone uppercase potential symbols
        words = text.upper().split()
        for word in words:
            clean = re.sub(r'[^A-Z]', '', word)
            if 2 <= len(clean) <= 5 and clean.isalpha():
                symbols.append(clean)

        return list(set(symbols))[:5]

    async def chat(self, user_message: str) -> Dict:
        """Process a user message and generate intelligent response."""

        # Extract any mentioned symbols
        symbols = self.extract_symbols(user_message)

        # Get relevant market data
        market_data = self.get_market_data(symbols)

        # Check if discussing bonds/treasury
        if any(word in user_message.lower() for word in ['treasury', 'bond', 't-bill', 'tbill']):
            market_data += "\n" + self.get_treasury_rates()

        # Get user context from memory
        user_context = self.memory.get_context_summary()

        # Build the enhanced message with context
        context_message = f"""User question: {user_message}

{f"REAL-TIME MARKET DATA:{chr(10)}{market_data}" if market_data else ""}

{f"USER CONTEXT:{chr(10)}{user_context}" if user_context else ""}

Provide a helpful, intelligent response. Use the real data above when relevant. Be specific and educational."""

        # Add to conversation history
        self.conversation_history.append({
            "role": "user",
            "content": context_message
        })

        # If no API key, provide intelligent fallback
        if not self.is_intelligent:
            response = self._intelligent_fallback(user_message, market_data)
            self.memory.add_conversation(user_message, response["message"])
            return response

        try:
            agent_response = None

            if self.provider == 'groq':
                # Call Groq API (Llama 3)
                chat_messages = [{"role": "system", "content": self.SYSTEM_PROMPT}]
                chat_messages.extend(self.conversation_history[-15:])

                response = self.groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=chat_messages,
                    max_tokens=2000,
                    temperature=0.7
                )
                agent_response = response.choices[0].message.content

            elif self.provider == 'anthropic':
                # Call Anthropic/Claude API
                response = self.anthropic_client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=2000,
                    system=self.SYSTEM_PROMPT,
                    messages=self.conversation_history[-15:]
                )
                agent_response = response.content[0].text

            if not agent_response:
                raise Exception("No response from LLM")

            # Add to conversation history
            self.conversation_history.append({
                "role": "assistant",
                "content": agent_response
            })

            # Save to memory
            self.memory.add_conversation(user_message, agent_response)

            return {
                "type": "intelligent_response",
                "message": agent_response,
                "has_real_data": bool(market_data),
                "symbols_analyzed": symbols,
                "powered_by": self.provider_name,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            # Fallback on error
            response = self._intelligent_fallback(user_message, market_data)
            response["error"] = str(e)
            return response

    def _intelligent_fallback(self, message: str, market_data: str) -> Dict:
        """Provide best possible response without API."""

        msg_lower = message.lower()

        # Treasury/Bonds vs Stocks/ETFs comparison
        if any(word in msg_lower for word in ['treasury', 'bond']) and any(word in msg_lower for word in ['stock', 'etf', 'equity']):
            return {
                "type": "comparison",
                "message": f"""**Treasury Bonds vs Stocks/ETFs - A Comprehensive Comparison**

{market_data if market_data else ""}

**Treasury Bonds (T-Bills, Notes, Bonds):**
- Risk: Extremely low (backed by US government)
- Returns: Currently ~4-5% for short-term T-bills
- Liquidity: High (can sell anytime)
- Tax: Federal tax on interest, exempt from state tax
- Best for: Capital preservation, emergency funds, near-term goals

**Stocks:**
- Risk: High (can lose 50%+ in crashes)
- Returns: Historically 7-10% annually long-term
- Liquidity: High for major stocks
- Tax: 15-20% on long-term gains, higher on short-term
- Best for: Long-term growth (5+ years)

**ETFs (like SPY, VTI):**
- Risk: Moderate to high (diversified but still equity)
- Returns: Tracks market, historically 7-10% annually
- Liquidity: Very high
- Tax: Similar to stocks
- Best for: Hands-off long-term investing

**My Analysis:**

For most people, a COMBINATION works best:
- Emergency fund (3-6 months expenses): Treasury bills or high-yield savings
- Near-term goals (1-3 years): Treasury bonds or bond ETFs
- Long-term wealth (5+ years): Stock ETFs like VTI or SPY

**The Key Question:**
When do you need this money? That determines the right mix.

*What's your timeline and risk tolerance?*""",
                "timestamp": datetime.now().isoformat(),
                "has_real_data": bool(market_data)
            }

        # If we have market data, provide analysis
        if market_data:
            return {
                "type": "analysis",
                "message": f"""Here's what I found:

{market_data}

**Analysis Notes:**
- RSI above 70 = potentially overbought
- RSI below 30 = potentially oversold
- Price above 50-day MA = short-term uptrend
- Price above 200-day MA = long-term uptrend
- Higher volatility = higher risk AND potential reward

**What to consider:**
1. How does this fit your overall portfolio?
2. What's your investment timeline?
3. Can you handle the volatility shown?

*Want me to dive deeper into any aspect?*""",
                "has_real_data": True,
                "timestamp": datetime.now().isoformat()
            }

        # General investment guidance
        return {
            "type": "guidance",
            "message": """I can help with that! To give you the best advice, tell me more:

1. **What options** are you comparing?
2. **Your timeline** - when do you need the money?
3. **Risk tolerance** - how would you feel if it dropped 20%?
4. **Specific stocks** - mention any tickers and I'll pull real data

**Things I can analyze:**
- Any stock (just mention ticker like AAPL, TSLA)
- Compare treasury bonds vs stocks vs ETFs
- Explain any investment concept
- Discuss portfolio strategies

Just ask naturally - I'm here to help!

*Note: For the most intelligent responses, ask your administrator to set up the ANTHROPIC_API_KEY.*""",
            "timestamp": datetime.now().isoformat()
        }

    def provide_feedback(self, correction: str):
        """Allow user to correct the agent for learning."""
        self.memory.add_correction(
            self.conversation_history[-2]["content"] if len(self.conversation_history) > 1 else "",
            correction
        )
        return {"status": "Feedback recorded. I'll learn from this!"}

    def clear_history(self):
        """Clear conversation history but keep learned preferences."""
        self.conversation_history = []
        return {"status": "Conversation cleared. I still remember your preferences."}


# Global instance
intelligent_agent = IntelligentFinanceAgent()

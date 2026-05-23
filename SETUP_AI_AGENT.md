# Setting Up the Intelligent AI Agent

The AI Advisor uses Claude (Anthropic's AI) to provide intelligent, conversational investment guidance.

## Quick Setup

1. **Get an Anthropic API Key**
   - Go to https://console.anthropic.com
   - Create an account or sign in
   - Generate an API key

2. **Add the API Key**

   **Option A: Environment Variable (Recommended)**
   ```bash
   export ANTHROPIC_API_KEY="your-api-key-here"
   ```
   Add this to your `~/.zshrc` or `~/.bashrc` for persistence.

   **Option B: Create a .env file**
   ```bash
   cd backend
   cp .env.example .env
   # Edit .env and add your key
   ```

3. **Restart the Server**
   ```bash
   cd backend
   pkill -f uvicorn
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

## What the Agent Can Do

With the API key configured, the agent can:
- Answer ANY finance question intelligently
- Compare investment options (bonds vs stocks vs ETFs)
- Analyze specific stocks with real-time data
- Explain concepts at any level of complexity
- Remember your preferences and conversation context
- Learn from your feedback

## Without API Key

Without the key, the agent falls back to:
- Pre-programmed responses for common questions
- Real-time stock data analysis
- Basic comparisons and explanations

## Cost

Anthropic API pricing (as of 2025):
- Claude Sonnet: ~$3 per million input tokens, ~$15 per million output tokens
- A typical conversation costs fractions of a cent
- Monthly cost for personal use: usually under $5

## Troubleshooting

**Agent not responding intelligently?**
- Check if ANTHROPIC_API_KEY is set: `echo $ANTHROPIC_API_KEY`
- Restart the backend server after setting the key
- Check server logs for errors

**Server won't start?**
- Make sure anthropic package is installed: `pip install anthropic`

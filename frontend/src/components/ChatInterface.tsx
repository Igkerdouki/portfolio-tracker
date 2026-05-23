import { useState, useEffect, useRef } from 'react';

interface Message {
  role: 'user' | 'agent';
  content: string;
  data?: any;
  timestamp: string;
}

interface ChatResponse {
  type: string;
  message: string;
  data?: any;
  [key: string]: any;
}

const API_URL = 'http://localhost:8000';

export function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchSuggestions();
    // Welcome message
    setMessages([{
      role: 'agent',
      content: "Hi! I'm your AI stock analyst. Ask me for stock recommendations, analysis, or market insights. Type 'help' to see what I can do!",
      timestamp: new Date().toISOString()
    }]);
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const fetchSuggestions = async () => {
    try {
      const res = await fetch(`${API_URL}/chat/suggestions`);
      const data = await res.json();
      setSuggestions(data.suggestions || []);
    } catch (error) {
      console.error('Failed to fetch suggestions:', error);
    }
  };

  const sendMessage = async (text: string) => {
    if (!text.trim()) return;

    const userMessage: Message = {
      role: 'user',
      content: text,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const res = await fetch(`${API_URL}/chat/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text })
      });

      const data: ChatResponse = await res.json();

      const agentMessage: Message = {
        role: 'agent',
        content: data.message || 'Response received',
        data: data,
        timestamp: new Date().toISOString()
      };

      setMessages(prev => [...prev, agentMessage]);
    } catch (error) {
      setMessages(prev => [...prev, {
        role: 'agent',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date().toISOString()
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage(input);
  };

  const renderMessageContent = (msg: Message) => {
    if (!msg.data) {
      return <p className="whitespace-pre-wrap">{msg.content}</p>;
    }

    const data = msg.data;

    switch (data.type) {
      case 'recommendations':
      case 'screening':
        return (
          <div>
            <p className="mb-3">{data.message}</p>
            <div className="space-y-2">
              {(data.data || data.results || []).map((stock: any, i: number) => (
                <div key={i} className="bg-gray-700 rounded-lg p-3">
                  <div className="flex justify-between items-center">
                    <span className="font-bold text-lg">{stock.symbol}</span>
                    <span className={`px-2 py-1 rounded text-sm ${stock.score > 60 ? 'bg-green-600' : stock.score > 30 ? 'bg-yellow-600' : 'bg-red-600'}`}>
                      Score: {stock.score}
                    </span>
                  </div>
                  <div className="text-sm text-gray-300 mt-1">
                    {stock.price && <span className="mr-3">Price: {stock.price}</span>}
                    {stock.return_1m && <span className="mr-3">1M Return: {stock.return_1m}</span>}
                    {stock.trend && <span className={stock.trend === 'BULLISH' ? 'text-green-400' : stock.trend === 'BEARISH' ? 'text-red-400' : 'text-gray-400'}>{stock.trend}</span>}
                  </div>
                  {stock.recommendation && (
                    <p className="text-xs text-gray-400 mt-1">{stock.recommendation}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        );

      case 'short_term':
        return (
          <div>
            <p className="mb-3">{data.message}</p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <h4 className="font-bold text-green-400 mb-2">Momentum Plays</h4>
                {(data.momentum_plays || []).map((s: any, i: number) => (
                  <div key={i} className="bg-gray-700 rounded p-2 mb-2">
                    <span className="font-bold">{s.symbol}</span>
                    <span className="ml-2 text-gray-400">{s.price}</span>
                    <span className={`ml-2 ${parseFloat(s.return_1w) > 0 ? 'text-green-400' : 'text-red-400'}`}>{s.return_1w}</span>
                  </div>
                ))}
              </div>
              <div>
                <h4 className="font-bold text-blue-400 mb-2">Reversal Plays</h4>
                {(data.reversal_plays || []).map((s: any, i: number) => (
                  <div key={i} className="bg-gray-700 rounded p-2 mb-2">
                    <span className="font-bold">{s.symbol}</span>
                    <span className="ml-2 text-gray-400">{s.price}</span>
                    <span className="ml-2 text-yellow-400">RSI: {s.rsi}</span>
                  </div>
                ))}
              </div>
            </div>
            {data.risk_warning && (
              <p className="text-yellow-500 text-sm mt-3">⚠️ {data.risk_warning}</p>
            )}
          </div>
        );

      case 'long_term':
        return (
          <div>
            <p className="mb-3">{data.message}</p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {['growth_stocks', 'value_stocks', 'dividend_stocks'].map(category => (
                <div key={category}>
                  <h4 className="font-bold text-purple-400 mb-2 capitalize">{category.replace('_', ' ')}</h4>
                  {(data[category] || []).map((s: any, i: number) => (
                    <div key={i} className="bg-gray-700 rounded p-2 mb-2 text-sm">
                      <span className="font-bold">{s.symbol}</span>
                      <span className="ml-2 text-gray-400">{s.price}</span>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          </div>
        );

      case 'stock_analysis':
        return (
          <div>
            <div className="flex items-center gap-3 mb-3">
              <span className="text-2xl font-bold">{data.symbol}</span>
              <span className="text-xl">{data.price_info?.current}</span>
              <span className={`${data.price_info?.change?.startsWith('+') ? 'text-green-400' : 'text-red-400'}`}>
                {data.price_info?.change}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-4 mb-4">
              <div className="bg-gray-700 rounded p-3">
                <h4 className="font-bold text-sm text-gray-400 mb-2">ML PREDICTION</h4>
                <p className={`text-xl font-bold ${data.ml_prediction?.direction === 'UP' ? 'text-green-400' : 'text-red-400'}`}>
                  {data.ml_prediction?.direction === 'UP' ? '📈' : '📉'} {data.ml_prediction?.direction}
                </p>
                <p className="text-xs text-gray-400 mt-1">{data.ml_prediction?.recommendation}</p>
              </div>
              <div className="bg-gray-700 rounded p-3">
                <h4 className="font-bold text-sm text-gray-400 mb-2">MODEL ACCURACY</h4>
                {Object.entries(data.model_accuracy || {}).map(([model, acc]: [string, any]) => (
                  <div key={model} className="flex justify-between text-sm">
                    <span className="text-gray-300">{model}</span>
                    <span>{acc}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-gray-700 rounded p-3">
              <h4 className="font-bold text-sm text-gray-400 mb-2">TECHNICAL LEVELS</h4>
              <div className="flex gap-4 text-sm">
                <span>SMA 50: {data.price_info?.sma_50}</span>
                <span>SMA 200: {data.price_info?.sma_200}</span>
                <span className={data.price_info?.above_sma50 ? 'text-green-400' : 'text-red-400'}>
                  {data.price_info?.above_sma50 ? '✓ Above 50MA' : '✗ Below 50MA'}
                </span>
              </div>
            </div>
          </div>
        );

      case 'market_overview':
        return (
          <div>
            <p className="mb-3">{data.message}</p>
            <div className="bg-gray-700 rounded-lg p-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <span className="text-gray-400">S&P 500 (1M)</span>
                  <p className={`text-lg font-bold ${data.data?.spy_return_1m > 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {data.data?.spy_return_1m?.toFixed(2)}%
                  </p>
                </div>
                <div>
                  <span className="text-gray-400">VIX</span>
                  <p className={`text-lg font-bold ${data.data?.vix < 20 ? 'text-green-400' : data.data?.vix < 30 ? 'text-yellow-400' : 'text-red-400'}`}>
                    {data.data?.vix?.toFixed(1)}
                  </p>
                </div>
                <div>
                  <span className="text-gray-400">Market Trend</span>
                  <p className={`font-bold ${data.data?.market_trend === 'BULLISH' ? 'text-green-400' : data.data?.market_trend === 'BEARISH' ? 'text-red-400' : 'text-gray-400'}`}>
                    {data.data?.market_trend}
                  </p>
                </div>
                <div>
                  <span className="text-gray-400">Environment</span>
                  <p className={`font-bold ${data.data?.trading_environment === 'RISK-ON' ? 'text-green-400' : 'text-red-400'}`}>
                    {data.data?.trading_environment}
                  </p>
                </div>
              </div>
              <p className="text-sm text-gray-300 mt-3">{data.interpretation}</p>
            </div>
          </div>
        );

      case 'explanation':
        return (
          <div className="bg-gray-700 rounded-lg p-4">
            <h4 className="font-bold text-lg text-purple-400 mb-2">{data.term}</h4>
            <p className="mb-2">{data.explanation}</p>
            {data.formula && (
              <p className="text-sm text-gray-400 font-mono bg-gray-800 p-2 rounded">
                Formula: {data.formula}
              </p>
            )}
          </div>
        );

      case 'help':
        return (
          <div>
            <p className="mb-3">{data.message}</p>
            <div className="space-y-3">
              {(data.capabilities || []).map((cap: any, i: number) => (
                <div key={i} className="bg-gray-700 rounded p-3">
                  <h4 className="font-bold text-green-400">{cap.command}</h4>
                  <div className="flex flex-wrap gap-2 mt-1">
                    {cap.examples.map((ex: string, j: number) => (
                      <button
                        key={j}
                        onClick={() => sendMessage(ex)}
                        className="text-xs bg-gray-600 hover:bg-gray-500 px-2 py-1 rounded"
                      >
                        {ex}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        );

      case 'comparison':
        return (
          <div>
            <p className="mb-3">{data.message}</p>
            <div className="grid grid-cols-2 gap-4">
              {(data.stocks || []).map((stock: any, i: number) => (
                <div key={i} className="bg-gray-700 rounded-lg p-4">
                  <h4 className="text-xl font-bold mb-2">{stock.symbol}</h4>
                  {stock.error ? (
                    <p className="text-red-400">{stock.error}</p>
                  ) : (
                    <>
                      <p className="text-lg">{stock.price}</p>
                      <p className={parseFloat(stock.return_1y) > 0 ? 'text-green-400' : 'text-red-400'}>
                        1Y Return: {stock.return_1y}
                      </p>
                      <p className="text-gray-400">Volatility: {stock.volatility}</p>
                      <p className={`font-bold mt-2 ${stock.prediction === 'UP' ? 'text-green-400' : 'text-red-400'}`}>
                        Prediction: {stock.prediction}
                      </p>
                    </>
                  )}
                </div>
              ))}
            </div>
          </div>
        );

      default:
        return (
          <div>
            <p className="whitespace-pre-wrap">{data.message || msg.content}</p>
            {data.suggestions && (
              <div className="flex flex-wrap gap-2 mt-3">
                {data.suggestions.map((s: string, i: number) => (
                  <button
                    key={i}
                    onClick={() => sendMessage(s)}
                    className="text-xs bg-gray-600 hover:bg-gray-500 px-2 py-1 rounded"
                  >
                    {s}
                  </button>
                ))}
              </div>
            )}
          </div>
        );
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-200px)] bg-gray-800 rounded-xl">
      {/* Header */}
      <div className="bg-gradient-to-r from-purple-600 to-blue-600 p-4 rounded-t-xl">
        <h2 className="text-xl font-bold flex items-center gap-2">
          <span>🤖</span> AI Stock Analyst
        </h2>
        <p className="text-sm text-gray-200">Ask me anything about stocks, recommendations, or market analysis</p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-lg p-3 ${
                msg.role === 'user'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-700 text-gray-100'
              }`}
            >
              {msg.role === 'agent' && (
                <div className="flex items-center gap-2 mb-2 text-xs text-gray-400">
                  <span>🤖 AI Analyst</span>
                  <span>{new Date(msg.timestamp).toLocaleTimeString()}</span>
                </div>
              )}
              {renderMessageContent(msg)}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-700 rounded-lg p-3">
              <div className="flex items-center gap-2">
                <div className="animate-bounce">🤔</div>
                <span className="text-gray-400">Analyzing...</span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Quick Actions */}
      <div className="px-4 pb-2">
        <div className="flex flex-wrap gap-2">
          {suggestions.slice(0, 5).map((s, i) => (
            <button
              key={i}
              onClick={() => sendMessage(s)}
              className="text-xs bg-gray-700 hover:bg-gray-600 px-3 py-1 rounded-full transition"
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-4 border-t border-gray-700">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about stocks, recommendations, or metrics..."
            className="flex-1 bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 px-6 py-2 rounded-lg font-medium transition"
          >
            {loading ? '...' : 'Send'}
          </button>
        </div>
      </form>
    </div>
  );
}

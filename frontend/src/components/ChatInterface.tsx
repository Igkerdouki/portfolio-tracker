import { useState, useEffect, useRef } from 'react';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  hasData?: boolean;
}

const API_URL = 'http://localhost:8000';

export function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setMessages([{
      role: 'assistant',
      content: `Hey! I'm Lili Claude, your personal investment advisor.

I'm here to help you navigate the markets and make smarter financial decisions - whether you're just starting out or already experienced.

**What I can help with:**
- Deep analysis of any stock or ETF
- Explain complex finance concepts simply
- Discuss investment strategies and timing
- Help you think through your portfolio decisions
- Compare different investment options

**Try asking me:**
- "What do you think about Tesla?"
- "Explain P/E ratio like I'm 5"
- "Should I invest in Apple for the long term?"
- "What's happening in the market today?"

So, what's on your mind?`,
      timestamp: new Date().toISOString()
    }]);
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

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

      const data = await res.json();

      const assistantMessage: Message = {
        role: 'assistant',
        content: data.message || 'Got your message but had trouble processing. Try rephrasing?',
        timestamp: new Date().toISOString(),
        hasData: data.has_real_data
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Having trouble connecting. Try again in a moment!`,
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

  const formatMessage = (content: string) => {
    return content
      .split('\n')
      .map((line, i) => {
        let formattedLine = line.replace(/\*\*(.*?)\*\*/g, '<strong style="color: #f59e0b">$1</strong>');
        formattedLine = formattedLine.replace(/\*(.*?)\*/g, '<em>$1</em>');
        formattedLine = formattedLine.replace(/`(.*?)`/g, '<code style="background: #1a1f4e; padding: 2px 6px; border-radius: 4px; font-size: 12px;">$1</code>');

        return (
          <span key={i}>
            <span dangerouslySetInnerHTML={{ __html: formattedLine }} />
            {i < content.split('\n').length - 1 && <br />}
          </span>
        );
      });
  };

  const quickPrompts = [
    "Recommend some stocks",
    "Explain P/E ratio",
    "Analyze AAPL",
    "Good beginner strategy?",
    "Market overview",
  ];

  return (
    <div className="flex flex-col h-[calc(100vh-200px)] min-h-[500px]">
      {/* Header */}
      <div className="p-5 border-b border-slate-700/50" style={{ backgroundColor: '#1a1f4e' }}>
        <h2 className="text-lg font-bold" style={{ color: '#f59e0b' }}>Lili Claude</h2>
        <p className="text-sm" style={{ color: '#94a3b8' }}>Powered by Claude • Your intelligent investment advisor</p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4" style={{ backgroundColor: '#0a0e27' }}>
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className="max-w-[85%] rounded-xl p-4"
              style={{
                backgroundColor: msg.role === 'user' ? '#f59e0b' : '#1a1f4e',
                color: msg.role === 'user' ? '#0a0e27' : '#e2e8f0',
                borderRadius: msg.role === 'user' ? '16px 16px 4px 16px' : '16px 16px 16px 4px'
              }}
            >
              {msg.role === 'assistant' && (
                <div className="flex items-center gap-2 mb-2 pb-2 border-b" style={{ borderColor: '#2a3158' }}>
                  <span className="text-sm font-medium" style={{ color: '#f59e0b' }}>Lili Claude</span>
                  {msg.hasData && (
                    <span className="text-xs px-2 py-0.5 rounded-full" style={{ backgroundColor: '#22c55e20', color: '#22c55e' }}>
                      Live Data
                    </span>
                  )}
                </div>
              )}
              <div className="whitespace-pre-wrap leading-relaxed text-sm">
                {formatMessage(msg.content)}
              </div>
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="rounded-xl p-4 max-w-[85%]" style={{ backgroundColor: '#1a1f4e' }}>
              <div className="flex items-center gap-3">
                <div className="flex space-x-1">
                  <div className="w-2 h-2 rounded-full animate-bounce" style={{ backgroundColor: '#f59e0b', animationDelay: '0ms' }}></div>
                  <div className="w-2 h-2 rounded-full animate-bounce" style={{ backgroundColor: '#f59e0b', animationDelay: '150ms' }}></div>
                  <div className="w-2 h-2 rounded-full animate-bounce" style={{ backgroundColor: '#f59e0b', animationDelay: '300ms' }}></div>
                </div>
                <span className="text-sm" style={{ color: '#94a3b8' }}>Thinking...</span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Quick Prompts */}
      {messages.length <= 2 && (
        <div className="px-4 py-3 border-t border-slate-700/50" style={{ backgroundColor: '#0d1230' }}>
          <p className="text-xs mb-2" style={{ color: '#64748b' }}>Quick questions:</p>
          <div className="flex flex-wrap gap-2">
            {quickPrompts.map((prompt, i) => (
              <button
                key={i}
                onClick={() => sendMessage(prompt)}
                className="text-sm px-3 py-1.5 rounded-full transition-all hover:scale-105"
                style={{ backgroundColor: '#1a1f4e', color: '#f59e0b', border: '1px solid #2a3158' }}
              >
                {prompt}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-4 border-t border-slate-700/50" style={{ backgroundColor: '#0d1230' }}>
        <div className="flex gap-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask me anything about investing..."
            className="flex-1 rounded-xl px-4 py-3 focus:outline-none text-white placeholder-slate-500"
            style={{ backgroundColor: '#1a1f4e', border: '1px solid #2a3158' }}
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="px-6 py-3 rounded-xl font-medium transition-all disabled:opacity-50"
            style={{ backgroundColor: '#f59e0b', color: '#0a0e27' }}
          >
            {loading ? '...' : 'Send'}
          </button>
        </div>
        <p className="text-xs mt-2 text-center" style={{ color: '#64748b' }}>
          Educational only. Not financial advice.
        </p>
      </form>
    </div>
  );
}

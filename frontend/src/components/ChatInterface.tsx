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
    // Welcome message
    setMessages([{
      role: 'assistant',
      content: `Hey there! 👋 Welcome to **Yiayia's Alpha** - your friendly investment buddy!

I'm here to help you understand investing and make smarter decisions. Whether you're a complete beginner or an experienced trader, I've got your back!

**What can I help you with?**
- 📊 Analyze any stock (just mention the name)
- 📚 Explain investing terms in simple English
- 💡 Discuss investment strategies
- ⚖️ Help you think through decisions

**Try asking me:**
- "Tell me about Tesla"
- "What does P/E ratio mean?"
- "Should I invest in Apple for the long term?"
- "Explain Sharpe ratio like I'm 5"

What would you like to explore? 😊`,
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
        content: data.message || 'I received your message but had trouble processing it. Could you try rephrasing?',
        timestamp: new Date().toISOString(),
        hasData: data.has_real_data
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Oops! I'm having a bit of trouble connecting right now. 😅

This could be because:
- The server is restarting
- There's a network hiccup

**Try again in a moment**, or ask me something else!`,
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
    // Simple markdown-like formatting
    return content
      .split('\n')
      .map((line, i) => {
        // Bold text
        let formattedLine = line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        // Italic
        formattedLine = formattedLine.replace(/\*(.*?)\*/g, '<em>$1</em>');
        // Code
        formattedLine = formattedLine.replace(/`(.*?)`/g, '<code class="bg-gray-600 px-1 rounded">$1</code>');

        return (
          <span key={i}>
            <span dangerouslySetInnerHTML={{ __html: formattedLine }} />
            {i < content.split('\n').length - 1 && <br />}
          </span>
        );
      });
  };

  const quickPrompts = [
    "What stocks should I look at?",
    "Explain P/E ratio simply",
    "Analyze AAPL for me",
    "What's a good beginner strategy?",
    "Is now a good time to invest?",
  ];

  return (
    <div className="flex flex-col h-[calc(100vh-180px)] bg-gradient-to-b from-gray-800 to-gray-900 rounded-xl shadow-2xl overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-purple-600 via-indigo-600 to-blue-600 p-5">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 bg-white/20 rounded-full flex items-center justify-center text-2xl">
            🧠
          </div>
          <div>
            <h2 className="text-xl font-bold">Yiayia's Alpha</h2>
            <p className="text-sm text-purple-200">Your friendly AI investment advisor</p>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[85%] rounded-2xl p-4 ${
                msg.role === 'user'
                  ? 'bg-gradient-to-r from-blue-500 to-blue-600 text-white rounded-br-sm'
                  : 'bg-gray-700/80 text-gray-100 rounded-bl-sm'
              }`}
            >
              {msg.role === 'assistant' && (
                <div className="flex items-center gap-2 mb-2 pb-2 border-b border-gray-600">
                  <span className="text-lg">🧠</span>
                  <span className="text-sm font-medium text-purple-400">Yiayia's Alpha</span>
                  {msg.hasData && (
                    <span className="text-xs bg-green-600/30 text-green-400 px-2 py-0.5 rounded-full">
                      📊 Live Data
                    </span>
                  )}
                </div>
              )}
              <div className="whitespace-pre-wrap leading-relaxed">
                {formatMessage(msg.content)}
              </div>
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-700/80 rounded-2xl rounded-bl-sm p-4 max-w-[85%]">
              <div className="flex items-center gap-3">
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{animationDelay: '0ms'}}></div>
                  <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{animationDelay: '150ms'}}></div>
                  <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{animationDelay: '300ms'}}></div>
                </div>
                <span className="text-gray-400 text-sm">Thinking about your question...</span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Quick Prompts */}
      {messages.length <= 2 && (
        <div className="px-4 pb-2">
          <p className="text-xs text-gray-500 mb-2">Quick questions to get started:</p>
          <div className="flex flex-wrap gap-2">
            {quickPrompts.map((prompt, i) => (
              <button
                key={i}
                onClick={() => sendMessage(prompt)}
                className="text-sm bg-gray-700/50 hover:bg-gray-600 border border-gray-600 px-3 py-1.5 rounded-full transition-all hover:scale-105"
              >
                {prompt}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-4 bg-gray-800/50 border-t border-gray-700">
        <div className="flex gap-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask me anything about investing..."
            className="flex-1 bg-gray-700 border border-gray-600 rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent placeholder-gray-400"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="bg-gradient-to-r from-purple-500 to-blue-500 hover:from-purple-600 hover:to-blue-600 disabled:from-gray-600 disabled:to-gray-600 px-6 py-3 rounded-xl font-medium transition-all hover:scale-105 disabled:scale-100"
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                </svg>
              </span>
            ) : (
              'Send'
            )}
          </button>
        </div>
        <p className="text-xs text-gray-500 mt-2 text-center">
          Educational purposes only. Not financial advice. Always do your own research.
        </p>
      </form>
    </div>
  );
}

import { useEffect, useState } from 'react';

const API_BASE_URL = 'http://localhost:8000';

interface TopPick {
  symbol: string;
  score: number;
  action: string;
  price: number;
  reasons: string[];
}

interface AgentStatus {
  running: boolean;
  analysis_count: number;
  improvement_cycles: number;
  pending_predictions: number;
  completed_predictions: number;
  last_analysis: string | null;
}

interface CacheStats {
  cached_symbols: string[];
  cache_size: number;
  hits: number;
  misses: number;
  hit_rate: string;
}

interface NewsSummary {
  article_count: number;
  sentiment: string;
  sentiment_score: number;
  bullish_articles: number;
  bearish_articles: number;
  recent_headlines: string[];
}

interface Analysis {
  symbol: string;
  price: number;
  overall_score: number;
  from_cache?: boolean;
  recommendation: {
    action: string;
    confidence: string;
    reasons: string[];
  };
  key_strengths: string[];
  key_concerns: string[];
  metrics: Record<string, number | string | boolean | null>;
  news_summary?: NewsSummary;
}

interface StockAnalysisProps {
  portfolioSymbols: string[];
}

export function StockAnalysis({ portfolioSymbols }: StockAnalysisProps) {
  const [watchlist, setWatchlist] = useState<string[]>([]);
  const [topPicks, setTopPicks] = useState<TopPick[]>([]);
  const [agentStatus, setAgentStatus] = useState<AgentStatus | null>(null);
  const [cacheStats, setCacheStats] = useState<CacheStats | null>(null);
  const [selectedAnalysis, setSelectedAnalysis] = useState<Analysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState<string | null>(null);
  const [newSymbol, setNewSymbol] = useState('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchStatus();
    fetchSuggestions();
    fetchCacheStats();
  }, []);

  const fetchStatus = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/analysis/agent-status`);
      const data = await res.json();
      setAgentStatus(data);
    } catch {
      // ignore
    }
  };

  const fetchSuggestions = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/analysis/suggestions`);
      const data = await res.json();
      setWatchlist(data.watchlist || []);
      setTopPicks(data.top_picks || []);
    } catch {
      // ignore
    }
  };

  const fetchCacheStats = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/analysis/cache-stats`);
      const data = await res.json();
      setCacheStats(data);
    } catch {
      // ignore
    }
  };

  const analyzeStock = async (symbol: string) => {
    setAnalyzing(symbol);
    setError(null);
    try {
      const res = await fetch(`${API_BASE_URL}/analysis/analyze/${symbol}`);
      const data = await res.json();
      if (data.error) {
        setError(data.error);
      } else {
        setSelectedAnalysis(data);
        fetchCacheStats();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analysis failed');
    } finally {
      setAnalyzing(null);
    }
  };

  const runCycle = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE_URL}/analysis/run-cycle`, { method: 'POST' });
      const data = await res.json();
      await fetchSuggestions();
      await fetchStatus();
      await fetchCacheStats();
      alert(`Analyzed ${data.symbols_analyzed} stocks. Check top picks!`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Cycle failed');
    } finally {
      setLoading(false);
    }
  };

  const startAgent = async () => {
    try {
      await fetch(`${API_BASE_URL}/analysis/start-agent?interval_hours=4`, { method: 'POST' });
      await fetchStatus();
    } catch {
      // ignore
    }
  };

  const stopAgent = async () => {
    try {
      await fetch(`${API_BASE_URL}/analysis/stop-agent`, { method: 'POST' });
      await fetchStatus();
    } catch {
      // ignore
    }
  };

  const addToWatchlist = async () => {
    if (!newSymbol.trim()) return;
    try {
      await fetch(`${API_BASE_URL}/analysis/watchlist/add`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify([newSymbol.toUpperCase()]),
      });
      setNewSymbol('');
      await fetchSuggestions();
    } catch {
      // ignore
    }
  };

  const removeFromWatchlist = async (symbol: string) => {
    try {
      await fetch(`${API_BASE_URL}/analysis/watchlist/remove`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify([symbol]),
      });
      await fetchSuggestions();
    } catch {
      // ignore
    }
  };

  const syncPortfolioToWatchlist = async () => {
    if (portfolioSymbols.length === 0) return;
    try {
      await fetch(`${API_BASE_URL}/analysis/watchlist/add`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(portfolioSymbols),
      });
      await fetchSuggestions();
    } catch {
      // ignore
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 70) return 'text-green-600';
    if (score >= 50) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getScoreBg = (score: number) => {
    if (score >= 70) return 'bg-green-500';
    if (score >= 50) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  const getActionColor = (action: string) => {
    if (action.includes('STRONG BUY')) return 'bg-green-600 text-white';
    if (action.includes('BUY')) return 'bg-green-100 text-green-800';
    if (action === 'ACCUMULATE') return 'bg-blue-100 text-blue-800';
    if (action === 'HOLD') return 'bg-yellow-100 text-yellow-800';
    if (action === 'REDUCE') return 'bg-orange-100 text-orange-800';
    return 'bg-red-100 text-red-800';
  };

  const getSentimentColor = (sentiment: string) => {
    if (sentiment === 'Bullish') return 'text-green-600';
    if (sentiment === 'Bearish') return 'text-red-600';
    return 'text-gray-600';
  };

  const formatMetricValue = (label: string, value: number | string | boolean | null) => {
    if (value === null || value === undefined) return 'N/A';
    if (typeof value === 'boolean') return value ? 'Yes' : 'No';
    if (typeof value === 'string') return value;

    if (label.includes('Growth') || label.includes('ROE') || label.includes('Margin')) {
      return `${(value * 100).toFixed(1)}%`;
    }
    if (label.includes('Position') || label.includes('RSI')) {
      return value.toFixed(0);
    }
    return value.toFixed(2);
  };

  return (
    <div className="space-y-6">
      {/* Agent Status Card */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-semibold text-gray-900">AI Analysis Agent</h2>
            <span
              className={`px-2 py-1 rounded-full text-xs font-medium ${
                agentStatus?.running ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
              }`}
            >
              {agentStatus?.running ? 'Running' : 'Stopped'}
            </span>
            {cacheStats && (
              <span className="text-xs text-gray-500">
                Cache: {cacheStats.cache_size} symbols ({cacheStats.hit_rate} hit rate)
              </span>
            )}
          </div>
          <div className="flex gap-2">
            <button
              onClick={runCycle}
              disabled={loading}
              className="bg-blue-600 hover:bg-blue-700 text-white text-sm px-4 py-2 rounded-lg disabled:opacity-50 transition-colors"
            >
              {loading ? 'Analyzing...' : 'Run Analysis'}
            </button>
            {!agentStatus?.running ? (
              <button
                onClick={startAgent}
                className="bg-green-600 hover:bg-green-700 text-white text-sm px-4 py-2 rounded-lg transition-colors"
              >
                Start Auto
              </button>
            ) : (
              <button
                onClick={stopAgent}
                className="bg-gray-500 hover:bg-gray-600 text-white text-sm px-4 py-2 rounded-lg transition-colors"
              >
                Stop
              </button>
            )}
          </div>
        </div>

        {agentStatus && (
          <div className="grid grid-cols-4 gap-4 text-sm">
            <div className="bg-gray-50 rounded-lg p-3">
              <span className="text-gray-500 text-xs">Analyses Run</span>
              <p className="font-semibold text-lg">{agentStatus.analysis_count}</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-3">
              <span className="text-gray-500 text-xs">Learning Cycles</span>
              <p className="font-semibold text-lg">{agentStatus.improvement_cycles}</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-3">
              <span className="text-gray-500 text-xs">Pending Predictions</span>
              <p className="font-semibold text-lg">{agentStatus.pending_predictions}</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-3">
              <span className="text-gray-500 text-xs">Last Analysis</span>
              <p className="font-semibold text-xs">
                {agentStatus.last_analysis
                  ? new Date(agentStatus.last_analysis).toLocaleString()
                  : 'Never'}
              </p>
            </div>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Picks */}
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="font-semibold text-gray-900 mb-3">Top Picks</h3>
          {topPicks.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <p className="mb-2">No recommendations yet</p>
              <p className="text-sm">Add stocks to watchlist and run analysis</p>
            </div>
          ) : (
            <div className="space-y-3">
              {topPicks.map((pick, index) => (
                <div
                  key={pick.symbol}
                  className="border border-gray-200 rounded-lg p-4 cursor-pointer hover:bg-gray-50 hover:border-blue-300 transition-all"
                  onClick={() => analyzeStock(pick.symbol)}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-gray-400 text-sm">#{index + 1}</span>
                      <span className="font-bold text-lg">{pick.symbol}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="text-right">
                        <span className={`text-2xl font-bold ${getScoreColor(pick.score)}`}>
                          {pick.score}
                        </span>
                        <span className="text-gray-400 text-sm">/100</span>
                      </div>
                      <span className={`px-3 py-1 rounded-lg text-sm font-medium ${getActionColor(pick.action)}`}>
                        {pick.action}
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center justify-between">
                    <p className="text-sm text-gray-600">${pick.price?.toFixed(2)}</p>
                    {/* Score bar */}
                    <div className="w-24 bg-gray-200 rounded-full h-2">
                      <div
                        className={`h-2 rounded-full ${getScoreBg(pick.score)}`}
                        style={{ width: `${pick.score}%` }}
                      />
                    </div>
                  </div>
                  {pick.reasons && pick.reasons.length > 0 && (
                    <p className="text-xs text-gray-500 mt-2 truncate">{pick.reasons[0]}</p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Watchlist */}
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-gray-900">Watchlist</h3>
            {portfolioSymbols.length > 0 && (
              <button
                onClick={syncPortfolioToWatchlist}
                className="text-blue-600 hover:text-blue-800 text-sm hover:underline"
              >
                + Add Portfolio ({portfolioSymbols.length})
              </button>
            )}
          </div>

          <div className="flex gap-2 mb-4">
            <input
              type="text"
              value={newSymbol}
              onChange={(e) => setNewSymbol(e.target.value.toUpperCase())}
              onKeyDown={(e) => e.key === 'Enter' && addToWatchlist()}
              placeholder="Add symbol (e.g., AAPL)..."
              className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
            />
            <button
              onClick={addToWatchlist}
              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm transition-colors"
            >
              Add
            </button>
          </div>

          {watchlist.length === 0 ? (
            <p className="text-gray-500 text-sm text-center py-4">No symbols in watchlist</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {watchlist.map((symbol) => (
                <span
                  key={symbol}
                  className="inline-flex items-center gap-2 bg-gray-100 hover:bg-gray-200 px-3 py-1.5 rounded-lg text-sm group transition-colors"
                >
                  <span
                    className="cursor-pointer hover:text-blue-600 font-medium"
                    onClick={() => analyzeStock(symbol)}
                  >
                    {analyzing === symbol ? (
                      <span className="inline-block animate-pulse">...</span>
                    ) : (
                      symbol
                    )}
                  </span>
                  <button
                    onClick={() => removeFromWatchlist(symbol)}
                    className="text-gray-400 hover:text-red-600 opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    x
                  </button>
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-red-500 hover:text-red-700">
            x
          </button>
        </div>
      )}

      {/* Selected Analysis Detail */}
      {selectedAnalysis && (
        <div className="bg-white rounded-lg shadow-lg p-6">
          {/* Header */}
          <div className="flex items-start justify-between mb-6 pb-4 border-b">
            <div>
              <div className="flex items-center gap-3">
                <h3 className="text-2xl font-bold">{selectedAnalysis.symbol}</h3>
                {selectedAnalysis.from_cache && (
                  <span className="text-xs bg-gray-100 text-gray-500 px-2 py-1 rounded">
                    Cached
                  </span>
                )}
              </div>
              <p className="text-gray-600 text-lg">${selectedAnalysis.price?.toFixed(2)}</p>
              {selectedAnalysis.metrics.name && (
                <p className="text-sm text-gray-500">{String(selectedAnalysis.metrics.name)}</p>
              )}
            </div>
            <div className="text-right">
              <div className="flex items-center gap-2 justify-end">
                <div className="w-16 bg-gray-200 rounded-full h-3">
                  <div
                    className={`h-3 rounded-full ${getScoreBg(selectedAnalysis.overall_score)}`}
                    style={{ width: `${selectedAnalysis.overall_score}%` }}
                  />
                </div>
                <p className={`text-4xl font-bold ${getScoreColor(selectedAnalysis.overall_score)}`}>
                  {selectedAnalysis.overall_score}
                </p>
              </div>
              <span
                className={`inline-block px-4 py-2 rounded-lg text-sm font-semibold mt-2 ${getActionColor(
                  selectedAnalysis.recommendation.action
                )}`}
              >
                {selectedAnalysis.recommendation.action}
              </span>
              <p className="text-xs text-gray-500 mt-1">
                Confidence: {selectedAnalysis.recommendation.confidence}
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Analysis & Reasons */}
            <div>
              <h4 className="font-semibold text-gray-900 mb-3">Analysis</h4>
              <ul className="space-y-2">
                {selectedAnalysis.recommendation.reasons.map((reason, i) => (
                  <li key={i} className="text-sm text-gray-700 flex items-start gap-2">
                    <span className="text-blue-500 mt-0.5">-</span>
                    {reason}
                  </li>
                ))}
              </ul>

              {selectedAnalysis.key_strengths.length > 0 && (
                <div className="mt-4">
                  <h5 className="font-medium text-green-700 mb-2">Strengths</h5>
                  <ul className="space-y-1">
                    {selectedAnalysis.key_strengths.map((s, i) => (
                      <li key={i} className="text-sm text-green-600 flex items-center gap-1">
                        <span>+</span> {s}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {selectedAnalysis.key_concerns.length > 0 && (
                <div className="mt-4">
                  <h5 className="font-medium text-red-700 mb-2">Concerns</h5>
                  <ul className="space-y-1">
                    {selectedAnalysis.key_concerns.map((c, i) => (
                      <li key={i} className="text-sm text-red-600 flex items-center gap-1">
                        <span>-</span> {c}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {/* Key Metrics */}
            <div>
              <h4 className="font-semibold text-gray-900 mb-3">Key Metrics</h4>
              <div className="space-y-2">
                {[
                  ['P/E Ratio', selectedAnalysis.metrics.pe_ratio],
                  ['PEG Ratio', selectedAnalysis.metrics.peg_ratio],
                  ['Price/Book', selectedAnalysis.metrics.price_to_book],
                  ['Debt/Equity', selectedAnalysis.metrics.debt_to_equity],
                  ['ROE', selectedAnalysis.metrics.roe],
                  ['Revenue Growth', selectedAnalysis.metrics.revenue_growth],
                  ['Profit Margin', selectedAnalysis.metrics.profit_margin],
                ].map(([label, value]) => (
                  <div key={label as string} className="flex justify-between text-sm py-1 border-b border-gray-100">
                    <span className="text-gray-600">{label}</span>
                    <span className="font-medium">
                      {formatMetricValue(label as string, value as number | string | boolean | null)}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Technical & Sentiment */}
            <div>
              <h4 className="font-semibold text-gray-900 mb-3">Technical & Sentiment</h4>
              <div className="space-y-2">
                {[
                  ['RSI', selectedAnalysis.metrics.rsi],
                  ['52W Position', selectedAnalysis.metrics.price_position_52w],
                  ['Above 50 MA', selectedAnalysis.metrics.above_ma_50],
                  ['Above 200 MA', selectedAnalysis.metrics.above_ma_200],
                  ['Golden Cross', selectedAnalysis.metrics.golden_cross],
                  ['MACD Signal', selectedAnalysis.metrics.macd_signal],
                ].map(([label, value]) => (
                  <div key={label as string} className="flex justify-between text-sm py-1 border-b border-gray-100">
                    <span className="text-gray-600">{label}</span>
                    <span className="font-medium">
                      {formatMetricValue(label as string, value as number | string | boolean | null)}
                    </span>
                  </div>
                ))}
              </div>

              {/* Sentiment Section */}
              {selectedAnalysis.news_summary && selectedAnalysis.news_summary.article_count > 0 && (
                <div className="mt-4 p-3 bg-gray-50 rounded-lg">
                  <h5 className="font-medium text-gray-700 mb-2">News Sentiment</h5>
                  <div className="flex items-center justify-between mb-2">
                    <span className={`font-semibold ${getSentimentColor(selectedAnalysis.news_summary.sentiment)}`}>
                      {selectedAnalysis.news_summary.sentiment}
                    </span>
                    <span className="text-xs text-gray-500">
                      {selectedAnalysis.news_summary.article_count} articles
                    </span>
                  </div>
                  {selectedAnalysis.news_summary.recent_headlines.length > 0 && (
                    <div className="text-xs text-gray-600 space-y-1 mt-2">
                      {selectedAnalysis.news_summary.recent_headlines.slice(0, 2).map((headline, i) => (
                        <p key={i} className="truncate">{headline}</p>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          <button
            onClick={() => setSelectedAnalysis(null)}
            className="mt-6 text-gray-500 hover:text-gray-700 text-sm flex items-center gap-1"
          >
            <span>&larr;</span> Close
          </button>
        </div>
      )}
    </div>
  );
}

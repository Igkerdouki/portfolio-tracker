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

interface Analysis {
  symbol: string;
  price: number;
  overall_score: number;
  recommendation: {
    action: string;
    confidence: string;
    reasons: string[];
  };
  key_strengths: string[];
  key_concerns: string[];
  metrics: Record<string, number | string | boolean | null>;
}

interface StockAnalysisProps {
  portfolioSymbols: string[];
}

export function StockAnalysis({ portfolioSymbols }: StockAnalysisProps) {
  const [watchlist, setWatchlist] = useState<string[]>([]);
  const [topPicks, setTopPicks] = useState<TopPick[]>([]);
  const [agentStatus, setAgentStatus] = useState<AgentStatus | null>(null);
  const [selectedAnalysis, setSelectedAnalysis] = useState<Analysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState<string | null>(null);
  const [newSymbol, setNewSymbol] = useState('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchStatus();
    fetchSuggestions();
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

  const getActionColor = (action: string) => {
    if (action.includes('BUY')) return 'bg-green-100 text-green-800';
    if (action === 'HOLD') return 'bg-yellow-100 text-yellow-800';
    return 'bg-red-100 text-red-800';
  };

  return (
    <div className="space-y-6">
      {/* Agent Status Card */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-semibold text-gray-900">Analysis Agent</h2>
            <span
              className={`px-2 py-1 rounded-full text-xs font-medium ${
                agentStatus?.running ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
              }`}
            >
              {agentStatus?.running ? 'Running' : 'Stopped'}
            </span>
          </div>
          <div className="flex gap-2">
            <button
              onClick={runCycle}
              disabled={loading}
              className="bg-blue-600 hover:bg-blue-700 text-white text-sm px-3 py-1.5 rounded disabled:opacity-50"
            >
              {loading ? 'Analyzing...' : 'Run Analysis'}
            </button>
            {!agentStatus?.running ? (
              <button
                onClick={startAgent}
                className="bg-green-600 hover:bg-green-700 text-white text-sm px-3 py-1.5 rounded"
              >
                Start Auto
              </button>
            ) : (
              <button
                onClick={stopAgent}
                className="bg-gray-500 hover:bg-gray-600 text-white text-sm px-3 py-1.5 rounded"
              >
                Stop
              </button>
            )}
          </div>
        </div>

        {agentStatus && (
          <div className="grid grid-cols-4 gap-4 text-sm">
            <div>
              <span className="text-gray-500">Analyses Run</span>
              <p className="font-semibold">{agentStatus.analysis_count}</p>
            </div>
            <div>
              <span className="text-gray-500">Learning Cycles</span>
              <p className="font-semibold">{agentStatus.improvement_cycles}</p>
            </div>
            <div>
              <span className="text-gray-500">Pending Predictions</span>
              <p className="font-semibold">{agentStatus.pending_predictions}</p>
            </div>
            <div>
              <span className="text-gray-500">Last Analysis</span>
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
            <p className="text-gray-500 text-sm">Run analysis to see recommendations</p>
          ) : (
            <div className="space-y-3">
              {topPicks.map((pick) => (
                <div
                  key={pick.symbol}
                  className="border border-gray-200 rounded-lg p-3 cursor-pointer hover:bg-gray-50"
                  onClick={() => analyzeStock(pick.symbol)}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-bold text-lg">{pick.symbol}</span>
                    <div className="flex items-center gap-2">
                      <span className={`font-semibold ${getScoreColor(pick.score)}`}>
                        {pick.score}/100
                      </span>
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${getActionColor(pick.action)}`}>
                        {pick.action}
                      </span>
                    </div>
                  </div>
                  <p className="text-sm text-gray-600">${pick.price?.toFixed(2)}</p>
                  {pick.reasons && pick.reasons.length > 0 && (
                    <p className="text-xs text-gray-500 mt-1">{pick.reasons[0]}</p>
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
                className="text-blue-600 hover:text-blue-800 text-xs"
              >
                + Add Portfolio
              </button>
            )}
          </div>

          <div className="flex gap-2 mb-3">
            <input
              type="text"
              value={newSymbol}
              onChange={(e) => setNewSymbol(e.target.value.toUpperCase())}
              onKeyDown={(e) => e.key === 'Enter' && addToWatchlist()}
              placeholder="Add symbol..."
              className="flex-1 border border-gray-300 rounded px-2 py-1 text-sm"
            />
            <button
              onClick={addToWatchlist}
              className="bg-blue-600 text-white px-3 py-1 rounded text-sm"
            >
              Add
            </button>
          </div>

          <div className="flex flex-wrap gap-2">
            {watchlist.map((symbol) => (
              <span
                key={symbol}
                className="inline-flex items-center gap-1 bg-gray-100 px-2 py-1 rounded text-sm group"
              >
                <span
                  className="cursor-pointer hover:text-blue-600"
                  onClick={() => analyzeStock(symbol)}
                >
                  {analyzing === symbol ? '...' : symbol}
                </span>
                <button
                  onClick={() => removeFromWatchlist(symbol)}
                  className="text-gray-400 hover:text-red-600 opacity-0 group-hover:opacity-100"
                >
                  x
                </button>
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {/* Selected Analysis Detail */}
      {selectedAnalysis && (
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-xl font-bold">{selectedAnalysis.symbol}</h3>
              <p className="text-gray-600">${selectedAnalysis.price?.toFixed(2)}</p>
            </div>
            <div className="text-right">
              <p className={`text-3xl font-bold ${getScoreColor(selectedAnalysis.overall_score)}`}>
                {selectedAnalysis.overall_score}/100
              </p>
              <span
                className={`inline-block px-3 py-1 rounded text-sm font-medium ${getActionColor(
                  selectedAnalysis.recommendation.action
                )}`}
              >
                {selectedAnalysis.recommendation.action}
              </span>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h4 className="font-semibold text-gray-900 mb-2">Analysis</h4>
              <ul className="space-y-1">
                {selectedAnalysis.recommendation.reasons.map((reason, i) => (
                  <li key={i} className="text-sm text-gray-700 flex items-start gap-2">
                    <span className="text-blue-500">-</span>
                    {reason}
                  </li>
                ))}
              </ul>

              {selectedAnalysis.key_strengths.length > 0 && (
                <div className="mt-4">
                  <h5 className="font-medium text-green-700 mb-1">Strengths</h5>
                  <ul className="text-sm text-green-600">
                    {selectedAnalysis.key_strengths.map((s, i) => (
                      <li key={i}>+ {s}</li>
                    ))}
                  </ul>
                </div>
              )}

              {selectedAnalysis.key_concerns.length > 0 && (
                <div className="mt-4">
                  <h5 className="font-medium text-red-700 mb-1">Concerns</h5>
                  <ul className="text-sm text-red-600">
                    {selectedAnalysis.key_concerns.map((c, i) => (
                      <li key={i}>- {c}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            <div>
              <h4 className="font-semibold text-gray-900 mb-2">Key Metrics</h4>
              <div className="space-y-2 text-sm">
                {[
                  ['P/E Ratio', selectedAnalysis.metrics.pe_ratio],
                  ['PEG Ratio', selectedAnalysis.metrics.peg_ratio],
                  ['Price/Book', selectedAnalysis.metrics.price_to_book],
                  ['Debt/Equity', selectedAnalysis.metrics.debt_to_equity],
                  ['ROE', selectedAnalysis.metrics.roe],
                  ['Revenue Growth', selectedAnalysis.metrics.revenue_growth],
                  ['52W Position', selectedAnalysis.metrics.price_position_52w],
                ].map(([label, value]) =>
                  value != null ? (
                    <div key={label as string} className="flex justify-between">
                      <span className="text-gray-600">{label}</span>
                      <span className="font-medium">
                        {typeof value === 'number'
                          ? String(label).includes('Growth') || String(label).includes('ROE')
                            ? `${((value as number) * 100).toFixed(1)}%`
                            : String(label).includes('Position')
                            ? `${(value as number).toFixed(0)}%`
                            : (value as number).toFixed(2)
                          : String(value)}
                      </span>
                    </div>
                  ) : null
                )}
              </div>
            </div>
          </div>

          <button
            onClick={() => setSelectedAnalysis(null)}
            className="mt-4 text-gray-500 hover:text-gray-700 text-sm"
          >
            Close
          </button>
        </div>
      )}
    </div>
  );
}

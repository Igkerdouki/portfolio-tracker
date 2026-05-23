import { useEffect, useState, useCallback } from 'react';

const API_BASE_URL = 'http://localhost:8000';

interface AgentStatus {
  name: string;
  role: string;
  running: boolean;
  actions_taken: number;
  successful_actions: number;
  success_rate: number;
  error_count: number;
  recent_errors: Array<{ timestamp: string; error: string }>;
  // Scanner specific
  watchlist?: string[];
  watchlist_size?: number;
  last_scan?: string;
  signals_found_today?: number;
  // Execution specific
  pending_orders?: number;
  executed_today?: number;
  daily_volume?: number;
  broker_connected?: boolean;
  // Journal specific
  total_trades_logged?: number;
  performance?: {
    total_trades: number;
    winning_trades: number;
    losing_trades: number;
    total_pnl: number;
  };
}

interface SystemStatus {
  orchestrator: {
    running: boolean;
    pending_signals: number;
    message_queue_size: number;
    total_messages: number;
  };
  agents: {
    scanner?: AgentStatus;
    execution?: AgentStatus;
    journal?: AgentStatus;
  };
  daily_stats: Record<string, { signals: number; trades: number; pnl: number }>;
}

interface Signal {
  symbol: string;
  action: string;
  signal?: string;
  price?: number;
  confidence?: number;
  reasons?: string[];
  timestamp?: string;
  source?: string;
  strategy?: string;
}

interface WebhookActivity {
  recent_alerts: number;
  keys: string[];
}

export function AgentDashboard() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [signals, setSignals] = useState<Signal[]>([]);
  const [webhookActivity, setWebhookActivity] = useState<WebhookActivity | null>(null);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [newSymbol, setNewSymbol] = useState('');
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/agents/status`);
      const data = await res.json();
      setStatus(data);
      setError(null);
    } catch (err) {
      setError('Failed to fetch agent status');
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchSignals = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/agents/scanner/signals`);
      const data = await res.json();
      setSignals(data.signals || []);
    } catch {
      // ignore
    }
  }, []);

  const fetchWebhookActivity = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/webhooks/tradingview/recent`);
      const data = await res.json();
      setWebhookActivity(data);
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    fetchSignals();
    fetchWebhookActivity();

    // Poll every 5 seconds
    const interval = setInterval(() => {
      fetchStatus();
      fetchSignals();
      fetchWebhookActivity();
    }, 5000);

    return () => clearInterval(interval);
  }, [fetchStatus, fetchSignals, fetchWebhookActivity]);

  const startAgents = async () => {
    setStarting(true);
    try {
      await fetch(`${API_BASE_URL}/agents/start`, { method: 'POST' });
      await fetchStatus();
    } catch (err) {
      setError('Failed to start agents');
    } finally {
      setStarting(false);
    }
  };

  const stopAgents = async () => {
    try {
      await fetch(`${API_BASE_URL}/agents/stop`, { method: 'POST' });
      await fetchStatus();
    } catch (err) {
      setError('Failed to stop agents');
    }
  };

  const triggerScan = async () => {
    try {
      await fetch(`${API_BASE_URL}/agents/scanner/scan-now`, { method: 'POST' });
      setTimeout(fetchSignals, 2000);
    } catch {
      // ignore
    }
  };

  const addToWatchlist = async () => {
    if (!newSymbol.trim()) return;
    try {
      await fetch(`${API_BASE_URL}/agents/scanner/watchlist`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbols: [newSymbol.toUpperCase()], action: 'add' }),
      });
      setNewSymbol('');
      await fetchStatus();
    } catch {
      // ignore
    }
  };

  const removeFromWatchlist = async (symbol: string) => {
    try {
      await fetch(`${API_BASE_URL}/agents/scanner/watchlist`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbols: [symbol], action: 'remove' }),
      });
      await fetchStatus();
    } catch {
      // ignore
    }
  };

  const testWebhook = async () => {
    try {
      await fetch(`${API_BASE_URL}/webhooks/tradingview/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbol: 'TEST',
          action: 'BUY',
          price: 100,
          strategy: 'Test Signal',
          message: 'Manual test from UI',
        }),
      });
      await fetchWebhookActivity();
      await fetchSignals();
    } catch {
      // ignore
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  const isRunning = status?.orchestrator?.running || false;
  const scanner = status?.agents?.scanner;
  const execution = status?.agents?.execution;
  const journal = status?.agents?.journal;

  return (
    <div className="space-y-6">
      {/* Error Banner */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-red-500 hover:text-red-700">x</button>
        </div>
      )}

      {/* Main Control Panel */}
      <div className="bg-white rounded-xl shadow-lg p-6">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-4">
            <h2 className="text-xl font-bold text-gray-900">Agentic Trading System</h2>
            <span className={`px-3 py-1 rounded-full text-sm font-medium ${
              isRunning
                ? 'bg-green-100 text-green-800 animate-pulse'
                : 'bg-gray-100 text-gray-600'
            }`}>
              {isRunning ? 'RUNNING' : 'STOPPED'}
            </span>
          </div>
          <div className="flex gap-3">
            {!isRunning ? (
              <button
                onClick={startAgents}
                disabled={starting}
                className="bg-green-600 hover:bg-green-700 text-white px-6 py-2 rounded-lg font-medium transition-colors disabled:opacity-50"
              >
                {starting ? 'Starting...' : 'Start Agents'}
              </button>
            ) : (
              <button
                onClick={stopAgents}
                className="bg-red-600 hover:bg-red-700 text-white px-6 py-2 rounded-lg font-medium transition-colors"
              >
                Stop Agents
              </button>
            )}
          </div>
        </div>

        {/* System Stats */}
        <div className="grid grid-cols-4 gap-4">
          <div className="bg-gray-50 rounded-lg p-4">
            <p className="text-sm text-gray-500">Pending Signals</p>
            <p className="text-2xl font-bold text-blue-600">{status?.orchestrator?.pending_signals || 0}</p>
          </div>
          <div className="bg-gray-50 rounded-lg p-4">
            <p className="text-sm text-gray-500">Message Queue</p>
            <p className="text-2xl font-bold text-purple-600">{status?.orchestrator?.message_queue_size || 0}</p>
          </div>
          <div className="bg-gray-50 rounded-lg p-4">
            <p className="text-sm text-gray-500">Total Messages</p>
            <p className="text-2xl font-bold text-gray-700">{status?.orchestrator?.total_messages || 0}</p>
          </div>
          <div className="bg-gray-50 rounded-lg p-4">
            <p className="text-sm text-gray-500">Active Agents</p>
            <p className="text-2xl font-bold text-green-600">
              {Object.values(status?.agents || {}).filter(a => a?.running).length} / 3
            </p>
          </div>
        </div>
      </div>

      {/* Agent Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Scanner Agent */}
        <div className="bg-white rounded-xl shadow p-5">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <div className={`w-3 h-3 rounded-full ${scanner?.running ? 'bg-green-500' : 'bg-gray-300'}`}></div>
              <h3 className="font-semibold text-gray-900">Scanner Agent</h3>
            </div>
            <button
              onClick={triggerScan}
              className="text-blue-600 hover:text-blue-800 text-sm"
            >
              Scan Now
            </button>
          </div>

          <div className="space-y-3 mb-4">
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">Watchlist Size</span>
              <span className="font-medium">{scanner?.watchlist_size || 0}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">Signals Found</span>
              <span className="font-medium text-green-600">{scanner?.signals_found_today || 0}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">Last Scan</span>
              <span className="font-medium text-xs">
                {scanner?.last_scan ? new Date(scanner.last_scan).toLocaleTimeString() : 'Never'}
              </span>
            </div>
          </div>

          {/* Watchlist Management */}
          <div className="border-t pt-4">
            <p className="text-xs text-gray-500 mb-2">Watchlist</p>
            <div className="flex gap-2 mb-3">
              <input
                type="text"
                value={newSymbol}
                onChange={(e) => setNewSymbol(e.target.value.toUpperCase())}
                onKeyDown={(e) => e.key === 'Enter' && addToWatchlist()}
                placeholder="Add symbol..."
                className="flex-1 border rounded px-2 py-1 text-sm"
              />
              <button
                onClick={addToWatchlist}
                className="bg-blue-600 text-white px-3 py-1 rounded text-sm"
              >
                +
              </button>
            </div>
            <div className="flex flex-wrap gap-1 max-h-24 overflow-y-auto">
              {scanner?.watchlist?.map((symbol) => (
                <span
                  key={symbol}
                  className="inline-flex items-center gap-1 bg-gray-100 px-2 py-0.5 rounded text-xs group"
                >
                  {symbol}
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

        {/* Execution Agent */}
        <div className="bg-white rounded-xl shadow p-5">
          <div className="flex items-center gap-2 mb-4">
            <div className={`w-3 h-3 rounded-full ${execution?.running ? 'bg-green-500' : 'bg-gray-300'}`}></div>
            <h3 className="font-semibold text-gray-900">Execution Agent</h3>
          </div>

          <div className="space-y-3 mb-4">
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">Broker</span>
              <span className={`font-medium ${execution?.broker_connected ? 'text-green-600' : 'text-red-600'}`}>
                {execution?.broker_connected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">Pending Orders</span>
              <span className="font-medium">{execution?.pending_orders || 0}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">Executed Today</span>
              <span className="font-medium text-blue-600">{execution?.executed_today || 0}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">Daily Volume</span>
              <span className="font-medium">${(execution?.daily_volume || 0).toLocaleString()}</span>
            </div>
          </div>

          <div className="border-t pt-4">
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">Success Rate</span>
              <span className="font-medium">
                {((execution?.success_rate || 0) * 100).toFixed(1)}%
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
              <div
                className="bg-green-500 h-2 rounded-full"
                style={{ width: `${(execution?.success_rate || 0) * 100}%` }}
              ></div>
            </div>
          </div>
        </div>

        {/* Journal Agent */}
        <div className="bg-white rounded-xl shadow p-5">
          <div className="flex items-center gap-2 mb-4">
            <div className={`w-3 h-3 rounded-full ${journal?.running ? 'bg-green-500' : 'bg-gray-300'}`}></div>
            <h3 className="font-semibold text-gray-900">Journal Agent</h3>
          </div>

          <div className="space-y-3 mb-4">
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">Trades Logged</span>
              <span className="font-medium">{journal?.total_trades_logged || 0}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">Total P&L</span>
              <span className={`font-medium ${(journal?.performance?.total_pnl || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                ${(journal?.performance?.total_pnl || 0).toFixed(2)}
              </span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">Win Rate</span>
              <span className="font-medium">
                {journal?.performance?.total_trades
                  ? ((journal.performance.winning_trades / journal.performance.total_trades) * 100).toFixed(1)
                  : 0}%
              </span>
            </div>
          </div>

          <div className="border-t pt-4">
            <div className="grid grid-cols-3 gap-2 text-center">
              <div>
                <p className="text-lg font-bold text-green-600">{journal?.performance?.winning_trades || 0}</p>
                <p className="text-xs text-gray-500">Wins</p>
              </div>
              <div>
                <p className="text-lg font-bold text-red-600">{journal?.performance?.losing_trades || 0}</p>
                <p className="text-xs text-gray-500">Losses</p>
              </div>
              <div>
                <p className="text-lg font-bold text-gray-600">{journal?.performance?.total_trades || 0}</p>
                <p className="text-xs text-gray-500">Total</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Signals & Webhooks */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Signals */}
        <div className="bg-white rounded-xl shadow p-5">
          <h3 className="font-semibold text-gray-900 mb-4">Recent Signals</h3>
          {signals.length === 0 ? (
            <p className="text-gray-500 text-sm text-center py-8">No signals yet. Start the agents and wait for scans.</p>
          ) : (
            <div className="space-y-3 max-h-64 overflow-y-auto">
              {signals.slice(0, 10).map((signal, idx) => (
                <div
                  key={idx}
                  className={`border rounded-lg p-3 ${
                    signal.action === 'BUY' ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'
                  }`}
                >
                  <div className="flex justify-between items-center">
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                        signal.action === 'BUY' ? 'bg-green-600 text-white' : 'bg-red-600 text-white'
                      }`}>
                        {signal.action}
                      </span>
                      <span className="font-bold">{signal.symbol}</span>
                    </div>
                    <span className="text-sm text-gray-600">
                      ${signal.price?.toFixed(2) || 'N/A'}
                    </span>
                  </div>
                  {signal.confidence && (
                    <div className="mt-2 flex items-center gap-2">
                      <span className="text-xs text-gray-500">Confidence:</span>
                      <div className="flex-1 bg-gray-200 rounded-full h-1.5">
                        <div
                          className="bg-blue-500 h-1.5 rounded-full"
                          style={{ width: `${signal.confidence * 100}%` }}
                        ></div>
                      </div>
                      <span className="text-xs font-medium">{(signal.confidence * 100).toFixed(0)}%</span>
                    </div>
                  )}
                  {signal.reasons && signal.reasons.length > 0 && (
                    <p className="text-xs text-gray-600 mt-1 truncate">{signal.reasons[0]}</p>
                  )}
                  {signal.source && (
                    <p className="text-xs text-gray-400 mt-1">Source: {signal.source}</p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* TradingView Webhooks */}
        <div className="bg-white rounded-xl shadow p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-900">TradingView Webhooks</h3>
            <button
              onClick={testWebhook}
              className="text-blue-600 hover:text-blue-800 text-sm"
            >
              Test Webhook
            </button>
          </div>

          <div className="bg-gray-50 rounded-lg p-4 mb-4">
            <p className="text-sm text-gray-500 mb-1">Webhook URL</p>
            <code className="text-xs bg-gray-200 px-2 py-1 rounded block overflow-x-auto">
              http://your-server:8000/webhooks/tradingview
            </code>
            <p className="text-xs text-gray-400 mt-2">
              Use ngrok to expose locally: <code>ngrok http 8000</code>
            </p>
          </div>

          <div className="space-y-3">
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">Recent Alerts</span>
              <span className="font-medium">{webhookActivity?.recent_alerts || 0}</span>
            </div>
          </div>

          {webhookActivity?.keys && webhookActivity.keys.length > 0 && (
            <div className="mt-4">
              <p className="text-xs text-gray-500 mb-2">Recent Activity</p>
              <div className="space-y-1 max-h-32 overflow-y-auto">
                {webhookActivity.keys.map((key, idx) => (
                  <div key={idx} className="text-xs bg-gray-100 px-2 py-1 rounded">
                    {key}
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="mt-4 border-t pt-4">
            <p className="text-sm font-medium text-gray-700 mb-2">Pine Script Alert Format</p>
            <pre className="text-xs bg-gray-900 text-green-400 p-3 rounded overflow-x-auto">
{`{
  "symbol": "{{ticker}}",
  "action": "BUY",
  "price": {{close}},
  "strategy": "My Strategy"
}`}
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
}

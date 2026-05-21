import { useState, useEffect } from 'react';

const API_BASE_URL = 'http://localhost:8000';

interface IBKRConnectProps {
  onSync: () => void;
}

export function IBKRConnect({ onSync }: IBKRConnectProps) {
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [port, setPort] = useState(7497);

  useEffect(() => {
    checkStatus();
  }, []);

  const checkStatus = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/ibkr/status`);
      const data = await res.json();
      setConnected(data.connected);
    } catch {
      setConnected(false);
    }
  };

  const handleConnect = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE_URL}/ibkr/connect?port=${port}`, {
        method: 'POST',
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Connection failed');
      }
      setConnected(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Connection failed');
    } finally {
      setLoading(false);
    }
  };

  const handleDisconnect = async () => {
    setLoading(true);
    try {
      await fetch(`${API_BASE_URL}/ibkr/disconnect`, { method: 'POST' });
      setConnected(false);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  const handleSync = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE_URL}/ibkr/sync`, { method: 'POST' });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Sync failed');
      }
      const data = await res.json();
      alert(`Synced ${data.positions_synced} positions from IBKR`);
      onSync();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Sync failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow p-4 mb-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h3 className="font-semibold text-gray-900">Interactive Brokers</h3>
          <span
            className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
              connected ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
            }`}
          >
            {connected ? 'Connected' : 'Disconnected'}
          </span>
        </div>

        <div className="flex items-center gap-3">
          {!connected && (
            <select
              value={port}
              onChange={(e) => setPort(Number(e.target.value))}
              className="border border-gray-300 rounded px-2 py-1 text-sm"
            >
              <option value={7497}>TWS Paper (7497)</option>
              <option value={7496}>TWS Live (7496)</option>
              <option value={4002}>Gateway Paper (4002)</option>
              <option value={4001}>Gateway Live (4001)</option>
            </select>
          )}

          {!connected ? (
            <button
              onClick={handleConnect}
              disabled={loading}
              className="bg-blue-600 hover:bg-blue-700 text-white text-sm px-4 py-1.5 rounded disabled:opacity-50"
            >
              {loading ? 'Connecting...' : 'Connect'}
            </button>
          ) : (
            <>
              <button
                onClick={handleSync}
                disabled={loading}
                className="bg-green-600 hover:bg-green-700 text-white text-sm px-4 py-1.5 rounded disabled:opacity-50"
              >
                {loading ? 'Syncing...' : 'Sync Positions'}
              </button>
              <button
                onClick={handleDisconnect}
                disabled={loading}
                className="bg-gray-500 hover:bg-gray-600 text-white text-sm px-4 py-1.5 rounded disabled:opacity-50"
              >
                Disconnect
              </button>
            </>
          )}
        </div>
      </div>

      {error && (
        <div className="mt-3 text-sm text-red-600 bg-red-50 px-3 py-2 rounded">
          {error}
        </div>
      )}

      {!connected && (
        <p className="mt-3 text-sm text-gray-500">
          Make sure TWS or IB Gateway is running and API connections are enabled in settings.
        </p>
      )}
    </div>
  );
}

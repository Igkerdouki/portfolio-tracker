import { useEffect, useState } from 'react';
import type { PortfolioSummary } from '../types';
import { api } from '../services/api';

interface DashboardProps {
  refreshTrigger: number;
}

interface IBKRAccount {
  by_currency?: {
    [key: string]: {
      UnrealizedPnL?: number;
      RealizedPnL?: number;
      NetLiquidation?: number;
      TotalCashValue?: number;
      GrossPositionValue?: number;
    };
  };
}

export function Dashboard({ refreshTrigger }: DashboardProps) {
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [ibkrAccount, setIbkrAccount] = useState<IBKRAccount | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [summaryData, accountData] = await Promise.all([
          api.getPortfolioSummary(),
          api.getIBKRAccount().catch(() => null),
        ]);
        setSummary(summaryData);
        setIbkrAccount(accountData);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch summary');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [refreshTrigger]);

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="bg-white rounded-lg shadow p-6 animate-pulse">
            <div className="h-4 bg-gray-200 rounded w-1/2 mb-2"></div>
            <div className="h-8 bg-gray-200 rounded w-3/4"></div>
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-6">
        {error}
      </div>
    );
  }

  if (!summary) return null;

  // Get real P&L from IBKR
  const usdPnL = ibkrAccount?.by_currency?.USD?.UnrealizedPnL ?? 0;
  const gbpPnL = ibkrAccount?.by_currency?.GBP?.UnrealizedPnL ?? 0;
  const basePnL = ibkrAccount?.by_currency?.BASE?.UnrealizedPnL ?? 0;
  const hasIBKRData = ibkrAccount?.by_currency && Object.keys(ibkrAccount.by_currency).length > 0;

  return (
    <div className="space-y-6 mb-6">
      {/* PROMINENT P&L SUMMARY - Always visible when IBKR connected */}
      {hasIBKRData ? (
        <div className={`rounded-xl shadow-lg p-6 ${basePnL >= 0 ? 'bg-gradient-to-r from-green-500 to-green-600' : 'bg-gradient-to-r from-red-500 to-red-600'}`}>
          <div className="text-white">
            <p className="text-sm font-medium opacity-90 mb-1">Total Trading P&L (Live from IBKR)</p>
            <div className="flex items-baseline gap-4 flex-wrap">
              <span className="text-4xl font-bold">
                {basePnL >= 0 ? '+' : ''}{basePnL.toLocaleString('en-US', { style: 'currency', currency: 'USD' })}
              </span>
              <span className="text-lg opacity-90">
                {basePnL >= 0 ? '▲' : '▼'} You're {basePnL >= 0 ? 'up' : 'down'}!
              </span>
            </div>
            <div className="mt-4 flex gap-6 flex-wrap">
              <div className="bg-white/20 rounded-lg px-4 py-2">
                <p className="text-xs opacity-75">USD Positions</p>
                <p className="text-xl font-semibold">
                  {usdPnL >= 0 ? '+' : ''}{usdPnL.toLocaleString('en-US', { style: 'currency', currency: 'USD' })}
                </p>
              </div>
              <div className="bg-white/20 rounded-lg px-4 py-2">
                <p className="text-xs opacity-75">GBP Positions</p>
                <p className="text-xl font-semibold">
                  {gbpPnL >= 0 ? '+' : ''}£{gbpPnL.toLocaleString('en-GB', { minimumFractionDigits: 2 })}
                </p>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="rounded-xl shadow-lg p-6 bg-gradient-to-r from-gray-400 to-gray-500">
          <div className="text-white">
            <p className="text-sm font-medium opacity-90 mb-1">Total Trading P&L</p>
            <p className="text-2xl font-bold">Connect to IBKR to see live P&L</p>
            <p className="text-sm opacity-75 mt-2">Click "Connect" above to sync your account data</p>
          </div>
        </div>
      )}

      {/* Portfolio Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-sm text-gray-500 mb-1">Total Cost Basis</p>
          <p className="text-2xl font-bold text-gray-900">
            ${summary.total_cost.toLocaleString('en-US', { minimumFractionDigits: 2 })}
          </p>
          <p className="text-xs text-gray-400 mt-1">Amount invested</p>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-sm text-gray-500 mb-1">Positions</p>
          <p className="text-2xl font-bold text-blue-600">{summary.positions_count}</p>
          <p className="text-xs text-gray-400 mt-1">Active holdings</p>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-sm text-gray-500 mb-1">USD P&L</p>
          <p className={`text-2xl font-bold ${usdPnL >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {usdPnL >= 0 ? '+' : ''}{usdPnL.toLocaleString('en-US', { style: 'currency', currency: 'USD' })}
          </p>
          <p className="text-xs text-gray-400 mt-1">Dollar positions</p>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-sm text-gray-500 mb-1">GBP P&L</p>
          <p className={`text-2xl font-bold ${gbpPnL >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {gbpPnL >= 0 ? '+' : ''}£{gbpPnL.toLocaleString('en-GB', { minimumFractionDigits: 2 })}
          </p>
          <p className="text-xs text-gray-400 mt-1">Pound positions</p>
        </div>
      </div>
    </div>
  );
}

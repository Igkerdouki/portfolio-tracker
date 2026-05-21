import { useEffect, useState } from 'react';
import type { PortfolioSummary } from '../types';
import { api } from '../services/api';

interface DashboardProps {
  refreshTrigger: number;
}

export function Dashboard({ refreshTrigger }: DashboardProps) {
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchSummary = async () => {
      try {
        setLoading(true);
        const data = await api.getPortfolioSummary();
        setSummary(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch summary');
      } finally {
        setLoading(false);
      }
    };

    fetchSummary();
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

  const cards = [
    {
      title: 'Total Value',
      value: `$${summary.total_value.toLocaleString('en-US', { minimumFractionDigits: 2 })}`,
      color: 'text-gray-900',
    },
    {
      title: 'Total Cost',
      value: `$${summary.total_cost.toLocaleString('en-US', { minimumFractionDigits: 2 })}`,
      color: 'text-gray-600',
    },
    {
      title: 'Total P&L',
      value: `$${summary.total_gain_loss.toLocaleString('en-US', { minimumFractionDigits: 2 })}`,
      color: summary.total_gain_loss >= 0 ? 'text-green-600' : 'text-red-600',
      subtitle: `${summary.total_gain_loss_percent >= 0 ? '+' : ''}${summary.total_gain_loss_percent.toFixed(2)}%`,
    },
    {
      title: 'Positions',
      value: summary.positions_count.toString(),
      color: 'text-blue-600',
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
      {cards.map((card) => (
        <div key={card.title} className="bg-white rounded-lg shadow p-6">
          <p className="text-sm text-gray-500 mb-1">{card.title}</p>
          <p className={`text-2xl font-bold ${card.color}`}>{card.value}</p>
          {card.subtitle && (
            <p className={`text-sm ${card.color}`}>{card.subtitle}</p>
          )}
        </div>
      ))}
    </div>
  );
}

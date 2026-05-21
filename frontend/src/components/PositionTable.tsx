import { useEffect, useState } from 'react';
import type { Position } from '../types';
import { api } from '../services/api';

interface PositionTableProps {
  refreshTrigger: number;
  onRefresh: () => void;
}

type SortKey = 'symbol' | 'shares' | 'current_value' | 'gain_loss' | 'gain_loss_percent';
type SortDirection = 'asc' | 'desc';

export function PositionTable({ refreshTrigger, onRefresh }: PositionTableProps) {
  const [positions, setPositions] = useState<Position[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>('symbol');
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc');
  const [deletingId, setDeletingId] = useState<number | null>(null);

  useEffect(() => {
    const fetchPositions = async () => {
      try {
        setLoading(true);
        const data = await api.getPositions();
        setPositions(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch positions');
      } finally {
        setLoading(false);
      }
    };

    fetchPositions();
  }, [refreshTrigger]);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortDirection('asc');
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this position?')) return;

    try {
      setDeletingId(id);
      await api.deletePosition(id);
      onRefresh();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete position');
    } finally {
      setDeletingId(null);
    }
  };

  const sortedPositions = [...positions].sort((a, b) => {
    let aVal = a[sortKey];
    let bVal = b[sortKey];

    if (aVal === null) aVal = 0;
    if (bVal === null) bVal = 0;

    if (typeof aVal === 'string') {
      return sortDirection === 'asc'
        ? aVal.localeCompare(bVal as string)
        : (bVal as string).localeCompare(aVal);
    }

    return sortDirection === 'asc'
      ? (aVal as number) - (bVal as number)
      : (bVal as number) - (aVal as number);
  });

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="p-6 animate-pulse">
          <div className="h-8 bg-gray-200 rounded mb-4"></div>
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-12 bg-gray-100 rounded mb-2"></div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
        {error}
      </div>
    );
  }

  const SortIcon = ({ columnKey }: { columnKey: SortKey }) => {
    if (sortKey !== columnKey) return null;
    return sortDirection === 'asc' ? ' ^' : ' v';
  };

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900">Positions</h2>
      </div>
      {positions.length === 0 ? (
        <div className="p-6 text-center text-gray-500">
          No positions yet. Add your first position above.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                  onClick={() => handleSort('symbol')}
                >
                  Symbol<SortIcon columnKey="symbol" />
                </th>
                <th
                  className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                  onClick={() => handleSort('shares')}
                >
                  Shares<SortIcon columnKey="shares" />
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Price
                </th>
                <th
                  className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                  onClick={() => handleSort('current_value')}
                >
                  Value<SortIcon columnKey="current_value" />
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Cost Basis
                </th>
                <th
                  className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                  onClick={() => handleSort('gain_loss')}
                >
                  P&L<SortIcon columnKey="gain_loss" />
                </th>
                <th
                  className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                  onClick={() => handleSort('gain_loss_percent')}
                >
                  P&L %<SortIcon columnKey="gain_loss_percent" />
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {sortedPositions.map((position) => (
                <tr key={position.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="font-medium text-gray-900">{position.symbol}</div>
                    <div className="text-sm text-gray-500">{position.asset_type}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-gray-900">
                    {position.shares.toLocaleString('en-US', { maximumFractionDigits: 4 })}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-gray-900">
                    {position.current_price
                      ? `$${position.current_price.toLocaleString('en-US', { minimumFractionDigits: 2 })}`
                      : '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-gray-900">
                    {position.current_value
                      ? `$${position.current_value.toLocaleString('en-US', { minimumFractionDigits: 2 })}`
                      : '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-gray-600">
                    ${position.cost_basis.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                  </td>
                  <td
                    className={`px-6 py-4 whitespace-nowrap text-right ${
                      position.gain_loss !== null
                        ? position.gain_loss >= 0
                          ? 'text-green-600'
                          : 'text-red-600'
                        : 'text-gray-400'
                    }`}
                  >
                    {position.gain_loss !== null
                      ? `${position.gain_loss >= 0 ? '+' : ''}$${position.gain_loss.toLocaleString('en-US', { minimumFractionDigits: 2 })}`
                      : '-'}
                  </td>
                  <td
                    className={`px-6 py-4 whitespace-nowrap text-right ${
                      position.gain_loss_percent !== null
                        ? position.gain_loss_percent >= 0
                          ? 'text-green-600'
                          : 'text-red-600'
                        : 'text-gray-400'
                    }`}
                  >
                    {position.gain_loss_percent !== null
                      ? `${position.gain_loss_percent >= 0 ? '+' : ''}${position.gain_loss_percent.toFixed(2)}%`
                      : '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right">
                    <button
                      onClick={() => handleDelete(position.id)}
                      disabled={deletingId === position.id}
                      className="text-red-600 hover:text-red-800 disabled:opacity-50"
                    >
                      {deletingId === position.id ? '...' : 'Delete'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

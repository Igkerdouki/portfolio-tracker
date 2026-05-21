import { useState } from 'react';
import type { PositionCreate, AssetType } from '../types';
import { api } from '../services/api';

interface AddPositionFormProps {
  onSuccess: () => void;
}

const ASSET_TYPES: { value: AssetType; label: string }[] = [
  { value: 'stock', label: 'Stock' },
  { value: 'etf', label: 'ETF' },
  { value: 'bond', label: 'Bond' },
  { value: 'crypto', label: 'Crypto' },
  { value: 'cash', label: 'Cash' },
  { value: 'other', label: 'Other' },
];

export function AddPositionForm({ onSuccess }: AddPositionFormProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState<PositionCreate>({
    symbol: '',
    shares: 0,
    cost_basis: 0,
    purchase_date: new Date().toISOString().split('T')[0],
    asset_type: 'stock',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!formData.symbol.trim()) {
      setError('Symbol is required');
      return;
    }
    if (formData.shares <= 0) {
      setError('Shares must be greater than 0');
      return;
    }
    if (formData.cost_basis < 0) {
      setError('Cost basis cannot be negative');
      return;
    }

    try {
      setLoading(true);
      await api.createPosition({
        ...formData,
        symbol: formData.symbol.toUpperCase().trim(),
      });
      setFormData({
        symbol: '',
        shares: 0,
        cost_basis: 0,
        purchase_date: new Date().toISOString().split('T')[0],
        asset_type: 'stock',
      });
      setIsOpen(false);
      onSuccess();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add position');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg transition-colors"
      >
        + Add Position
      </button>
    );
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
        <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
          <h2 className="text-lg font-semibold text-gray-900">Add Position</h2>
          <button
            onClick={() => setIsOpen(false)}
            className="text-gray-400 hover:text-gray-600"
          >
            X
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-2 rounded text-sm">
              {error}
            </div>
          )}

          <div>
            <label htmlFor="symbol" className="block text-sm font-medium text-gray-700 mb-1">
              Symbol
            </label>
            <input
              type="text"
              id="symbol"
              value={formData.symbol}
              onChange={(e) => setFormData({ ...formData, symbol: e.target.value })}
              placeholder="e.g., AAPL"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <div>
            <label htmlFor="shares" className="block text-sm font-medium text-gray-700 mb-1">
              Shares
            </label>
            <input
              type="number"
              id="shares"
              value={formData.shares || ''}
              onChange={(e) => setFormData({ ...formData, shares: parseFloat(e.target.value) || 0 })}
              step="any"
              min="0"
              placeholder="e.g., 10"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <div>
            <label htmlFor="cost_basis" className="block text-sm font-medium text-gray-700 mb-1">
              Total Cost Basis ($)
            </label>
            <input
              type="number"
              id="cost_basis"
              value={formData.cost_basis || ''}
              onChange={(e) => setFormData({ ...formData, cost_basis: parseFloat(e.target.value) || 0 })}
              step="any"
              min="0"
              placeholder="e.g., 1500.00"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <div>
            <label htmlFor="purchase_date" className="block text-sm font-medium text-gray-700 mb-1">
              Purchase Date
            </label>
            <input
              type="date"
              id="purchase_date"
              value={formData.purchase_date}
              onChange={(e) => setFormData({ ...formData, purchase_date: e.target.value })}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <div>
            <label htmlFor="asset_type" className="block text-sm font-medium text-gray-700 mb-1">
              Asset Type
            </label>
            <select
              id="asset_type"
              value={formData.asset_type}
              onChange={(e) => setFormData({ ...formData, asset_type: e.target.value as AssetType })}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              {ASSET_TYPES.map((type) => (
                <option key={type.value} value={type.value}>
                  {type.label}
                </option>
              ))}
            </select>
          </div>

          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={() => setIsOpen(false)}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? 'Adding...' : 'Add Position'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

import { useEffect, useState } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import type { PortfolioSummary, AllocationItem } from '../types';
import { api } from '../services/api';

interface AllocationChartProps {
  refreshTrigger: number;
}

const COLORS = [
  '#3B82F6', // blue
  '#10B981', // green
  '#F59E0B', // amber
  '#EF4444', // red
  '#8B5CF6', // purple
  '#EC4899', // pink
  '#06B6D4', // cyan
  '#F97316', // orange
];

export function AllocationChart({ refreshTrigger }: AllocationChartProps) {
  const [allocation, setAllocation] = useState<AllocationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchAllocation = async () => {
      try {
        setLoading(true);
        const data: PortfolioSummary = await api.getPortfolioSummary();
        setAllocation(data.allocation);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch allocation');
      } finally {
        setLoading(false);
      }
    };

    fetchAllocation();
  }, [refreshTrigger]);

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="h-4 bg-gray-200 rounded w-1/3 mb-4"></div>
        <div className="h-64 flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Asset Allocation</h2>
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      </div>
    );
  }

  if (allocation.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Asset Allocation</h2>
        <div className="h-64 flex items-center justify-center text-gray-500">
          No allocation data available
        </div>
      </div>
    );
  }

  const chartData = allocation.map((item) => ({
    name: item.asset_type.charAt(0).toUpperCase() + item.asset_type.slice(1),
    value: item.value,
    percentage: item.percentage,
  }));

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Asset Allocation</h2>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              innerRadius={60}
              outerRadius={80}
              paddingAngle={2}
              dataKey="value"
            >
              {chartData.map((_, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value: number) => [
                `$${value.toLocaleString('en-US', { minimumFractionDigits: 2 })}`,
                'Value',
              ]}
            />
            <Legend
              formatter={(value, entry) => {
                const item = chartData.find((d) => d.name === value);
                return `${value} (${item?.percentage.toFixed(1)}%)`;
              }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

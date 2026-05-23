import { useState, useCallback } from 'react';

const API_BASE_URL = 'http://localhost:8000';

interface Prediction {
  direction: string;
  confidence: number;
  up_probability: number;
  down_probability: number;
  predicted_return?: number;
  predicted_return_pct?: number;
}

interface BacktestResult {
  strategy: string;
  total_return_pct: number;
  annual_return_pct: number;
  sharpe_ratio: number;
  max_drawdown_pct: number;
  win_rate_pct: number;
  total_trades: number;
  final_equity: number;
}

interface MonteCarloResult {
  n_simulations: number;
  return_statistics: {
    mean: number;
    median: number;
    std: number;
    percentile_5: number;
    percentile_95: number;
    probability_positive: number;
  };
  sharpe_statistics: {
    mean: number;
    median: number;
  };
  drawdown_statistics: {
    mean: number;
    worst_5_percentile: number;
  };
}

interface FullResult {
  symbol: string;
  model_type: string;
  data_info: {
    total_samples: number;
    training_samples: number;
    test_samples: number;
    date_range: { start: string; end: string };
    test_period?: { start: string; end: string };
  };
  training: {
    cv_accuracy?: number;
    cv_std?: number;
    feature_importance?: Record<string, number>;
  };
  backtest: {
    long_short: BacktestResult;
    long_only: BacktestResult;
    buy_hold: BacktestResult;
    full_period_buy_hold_pct?: number;
    note?: string;
  };
  monte_carlo: MonteCarloResult;
  current_prediction: Prediction;
  comparison: {
    long_short_vs_buy_hold: number;
    sharpe_improvement: number;
  };
}

export function MLPredictor() {
  const [symbol, setSymbol] = useState('SPY');
  const [modelType, setModelType] = useState('random_forest');
  const [period, setPeriod] = useState('5y');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<FullResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [quickPrediction, setQuickPrediction] = useState<Prediction | null>(null);

  const runBacktest = useCallback(async () => {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await fetch(`${API_BASE_URL}/ml/backtest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol, model_type: modelType, period })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to run backtest');
      }

      const data = await res.json();
      setResult(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [symbol, modelType, period]);

  const getQuickPrediction = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/ml/predict`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to get prediction');
      }

      const data = await res.json();
      setQuickPrediction(data.prediction);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  }, [symbol]);

  return (
    <div className="space-y-6">
      {/* Header & Controls */}
      <div className="bg-white rounded-xl shadow-lg p-6">
        <h2 className="text-xl font-bold text-gray-900 mb-4">ML Price Predictor & Backtester</h2>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
          <div>
            <label className="block text-sm text-gray-600 mb-1">Symbol</label>
            <input
              type="text"
              value={symbol}
              onChange={(e) => setSymbol(e.target.value.toUpperCase())}
              className="w-full border rounded-lg px-3 py-2"
              placeholder="SPY"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">Model</label>
            <select
              value={modelType}
              onChange={(e) => setModelType(e.target.value)}
              className="w-full border rounded-lg px-3 py-2 bg-white"
            >
              <option value="random_forest">Random Forest</option>
              <option value="lstm">LSTM (Neural Network)</option>
            </select>
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">Data Period</label>
            <select
              value={period}
              onChange={(e) => setPeriod(e.target.value)}
              className="w-full border rounded-lg px-3 py-2 bg-white"
            >
              <option value="2y">2 Years</option>
              <option value="5y">5 Years</option>
              <option value="10y">10 Years</option>
              <option value="max">Max Available</option>
            </select>
          </div>
          <div className="flex items-end gap-2">
            <button
              onClick={runBacktest}
              disabled={loading}
              className="flex-1 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium disabled:opacity-50"
            >
              {loading ? 'Running...' : 'Run Backtest'}
            </button>
            <button
              onClick={getQuickPrediction}
              className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg font-medium"
              title="Quick prediction"
            >
              Predict
            </button>
          </div>
        </div>

        {/* Quick Prediction Result */}
        {quickPrediction && (
          <div className={`p-4 rounded-lg ${quickPrediction.direction === 'UP' ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className={`text-3xl ${quickPrediction.direction === 'UP' ? 'text-green-600' : 'text-red-600'}`}>
                  {quickPrediction.direction === 'UP' ? '↑' : '↓'}
                </span>
                <div>
                  <p className="font-bold text-lg">{symbol} - Next Day: {quickPrediction.direction}</p>
                  <p className="text-sm text-gray-600">
                    Confidence: {(quickPrediction.confidence * 100).toFixed(1)}%
                    {quickPrediction.predicted_return_pct && (
                      <span className="ml-2">
                        | Expected Return: {quickPrediction.predicted_return_pct.toFixed(2)}%
                      </span>
                    )}
                  </p>
                </div>
              </div>
              <div className="text-right">
                <p className="text-sm text-gray-500">Probability</p>
                <p className="text-green-600">Up: {(quickPrediction.up_probability * 100).toFixed(1)}%</p>
                <p className="text-red-600">Down: {(quickPrediction.down_probability * 100).toFixed(1)}%</p>
              </div>
            </div>
          </div>
        )}

        {error && (
          <div className="mt-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
            {error}
          </div>
        )}
      </div>

      {/* Loading State */}
      {loading && (
        <div className="bg-white rounded-xl shadow-lg p-12 text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Training model and running backtest...</p>
          <p className="text-sm text-gray-400 mt-2">This may take a minute for large datasets</p>
        </div>
      )}

      {/* Results */}
      {result && !loading && (
        <>
          {/* Data Info */}
          <div className="bg-white rounded-xl shadow p-6">
            <h3 className="font-semibold text-gray-900 mb-4">Data & Training Info</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-gray-50 rounded-lg p-3">
                <p className="text-sm text-gray-500">Total Samples</p>
                <p className="text-xl font-bold">{result.data_info.total_samples}</p>
              </div>
              <div className="bg-gray-50 rounded-lg p-3">
                <p className="text-sm text-gray-500">Training Set</p>
                <p className="text-xl font-bold">{result.data_info.training_samples}</p>
              </div>
              <div className="bg-gray-50 rounded-lg p-3">
                <p className="text-sm text-gray-500">Test Set</p>
                <p className="text-xl font-bold">{result.data_info.test_samples}</p>
              </div>
              <div className="bg-gray-50 rounded-lg p-3">
                <p className="text-sm text-gray-500">CV Accuracy</p>
                <p className="text-xl font-bold">
                  {result.training.cv_accuracy ? (result.training.cv_accuracy * 100).toFixed(1) + '%' : 'N/A'}
                </p>
              </div>
            </div>
            <div className="mt-3 text-xs text-gray-400 space-y-1">
              <p>Full data: {result.data_info.date_range.start} to {result.data_info.date_range.end}</p>
              {result.data_info.test_period && (
                <p className="text-amber-600 font-medium">
                  ⚠️ Test period: {result.data_info.test_period.start} to {result.data_info.test_period.end} (last {result.data_info.test_samples} days)
                </p>
              )}
            </div>
          </div>

          {/* Strategy Comparison */}
          <div className="bg-white rounded-xl shadow p-6">
            <div className="flex justify-between items-start mb-4">
              <div>
                <h3 className="font-semibold text-gray-900">Strategy Comparison (Test Period)</h3>
                {result.backtest.note && (
                  <p className="text-xs text-amber-600 mt-1">{result.backtest.note}</p>
                )}
              </div>
              {result.backtest.full_period_buy_hold_pct !== undefined && (
                <div className="text-right bg-gray-50 rounded-lg px-3 py-2">
                  <p className="text-xs text-gray-500">Full Period Buy & Hold</p>
                  <p className={`text-lg font-bold ${result.backtest.full_period_buy_hold_pct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {result.backtest.full_period_buy_hold_pct >= 0 ? '+' : ''}{result.backtest.full_period_buy_hold_pct.toFixed(2)}%
                  </p>
                </div>
              )}
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-2 px-3">Strategy</th>
                    <th className="text-right py-2 px-3">Total Return</th>
                    <th className="text-right py-2 px-3">Annual Return</th>
                    <th className="text-right py-2 px-3">Sharpe Ratio</th>
                    <th className="text-right py-2 px-3">Max Drawdown</th>
                    <th className="text-right py-2 px-3">Win Rate</th>
                    <th className="text-right py-2 px-3">Final Equity</th>
                  </tr>
                </thead>
                <tbody>
                  {['long_short', 'long_only', 'buy_hold'].map((strategy) => {
                    const bt = result.backtest[strategy as keyof typeof result.backtest];
                    const isBest = bt.total_return_pct === Math.max(
                      result.backtest.long_short.total_return_pct,
                      result.backtest.long_only.total_return_pct,
                      result.backtest.buy_hold.total_return_pct
                    );
                    return (
                      <tr key={strategy} className={`border-b ${isBest ? 'bg-green-50' : ''}`}>
                        <td className="py-2 px-3 font-medium">
                          {strategy === 'long_short' ? 'Long/Short (ML)' :
                           strategy === 'long_only' ? 'Long Only (ML)' : 'Buy & Hold'}
                          {isBest && <span className="ml-2 text-green-600 text-xs">BEST</span>}
                        </td>
                        <td className={`text-right py-2 px-3 font-bold ${bt.total_return_pct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {bt.total_return_pct.toFixed(2)}%
                        </td>
                        <td className={`text-right py-2 px-3 ${bt.annual_return_pct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {bt.annual_return_pct.toFixed(2)}%
                        </td>
                        <td className="text-right py-2 px-3">{bt.sharpe_ratio.toFixed(2)}</td>
                        <td className="text-right py-2 px-3 text-red-600">{bt.max_drawdown_pct.toFixed(2)}%</td>
                        <td className="text-right py-2 px-3">{bt.win_rate_pct.toFixed(1)}%</td>
                        <td className="text-right py-2 px-3">${bt.final_equity.toLocaleString(undefined, {maximumFractionDigits: 0})}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-4">
              <div className={`p-3 rounded-lg ${result.comparison.long_short_vs_buy_hold >= 0 ? 'bg-green-50' : 'bg-red-50'}`}>
                <p className="text-sm text-gray-600">Long/Short vs Buy & Hold</p>
                <p className={`text-xl font-bold ${result.comparison.long_short_vs_buy_hold >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {result.comparison.long_short_vs_buy_hold >= 0 ? '+' : ''}{result.comparison.long_short_vs_buy_hold.toFixed(2)}%
                </p>
              </div>
              <div className={`p-3 rounded-lg ${result.comparison.sharpe_improvement >= 0 ? 'bg-green-50' : 'bg-red-50'}`}>
                <p className="text-sm text-gray-600">Sharpe Ratio Improvement</p>
                <p className={`text-xl font-bold ${result.comparison.sharpe_improvement >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {result.comparison.sharpe_improvement >= 0 ? '+' : ''}{result.comparison.sharpe_improvement.toFixed(2)}
                </p>
              </div>
            </div>
          </div>

          {/* Monte Carlo Results */}
          <div className="bg-white rounded-xl shadow p-6">
            <h3 className="font-semibold text-gray-900 mb-4">
              Monte Carlo Simulation ({result.monte_carlo.n_simulations.toLocaleString()} simulations)
            </h3>
            <p className="text-sm text-gray-500 mb-4">
              Returns are resampled to generate many possible equity paths, providing a distribution of outcomes instead of a single backtest result.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Return Distribution */}
              <div className="bg-gray-50 rounded-lg p-4">
                <h4 className="font-medium text-gray-700 mb-3">Return Distribution</h4>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-500">Mean Return</span>
                    <span className={`font-medium ${result.monte_carlo.return_statistics.mean >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {result.monte_carlo.return_statistics.mean.toFixed(2)}%
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Median Return</span>
                    <span className="font-medium">{result.monte_carlo.return_statistics.median.toFixed(2)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Std Deviation</span>
                    <span className="font-medium">{result.monte_carlo.return_statistics.std.toFixed(2)}%</span>
                  </div>
                  <div className="border-t pt-2 mt-2">
                    <div className="flex justify-between">
                      <span className="text-gray-500">5th Percentile</span>
                      <span className="font-medium text-red-600">{result.monte_carlo.return_statistics.percentile_5.toFixed(2)}%</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">95th Percentile</span>
                      <span className="font-medium text-green-600">{result.monte_carlo.return_statistics.percentile_95.toFixed(2)}%</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Probability of Profit */}
              <div className="bg-gray-50 rounded-lg p-4">
                <h4 className="font-medium text-gray-700 mb-3">Probability of Profit</h4>
                <div className="text-center py-4">
                  <p className={`text-4xl font-bold ${result.monte_carlo.return_statistics.probability_positive >= 50 ? 'text-green-600' : 'text-red-600'}`}>
                    {result.monte_carlo.return_statistics.probability_positive.toFixed(1)}%
                  </p>
                  <p className="text-sm text-gray-500 mt-2">chance of positive return</p>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-4 mt-4">
                  <div
                    className={`h-4 rounded-full ${result.monte_carlo.return_statistics.probability_positive >= 50 ? 'bg-green-500' : 'bg-red-500'}`}
                    style={{ width: `${result.monte_carlo.return_statistics.probability_positive}%` }}
                  ></div>
                </div>
              </div>

              {/* Risk Metrics */}
              <div className="bg-gray-50 rounded-lg p-4">
                <h4 className="font-medium text-gray-700 mb-3">Risk Metrics</h4>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-500">Mean Sharpe</span>
                    <span className="font-medium">{result.monte_carlo.sharpe_statistics.mean.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Median Sharpe</span>
                    <span className="font-medium">{result.monte_carlo.sharpe_statistics.median.toFixed(2)}</span>
                  </div>
                  <div className="border-t pt-2 mt-2">
                    <div className="flex justify-between">
                      <span className="text-gray-500">Mean Max Drawdown</span>
                      <span className="font-medium text-red-600">{result.monte_carlo.drawdown_statistics.mean.toFixed(2)}%</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">Worst 5% Drawdown</span>
                      <span className="font-medium text-red-600">{result.monte_carlo.drawdown_statistics.worst_5_percentile.toFixed(2)}%</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Feature Importance */}
          {result.training.feature_importance && (
            <div className="bg-white rounded-xl shadow p-6">
              <h3 className="font-semibold text-gray-900 mb-4">Top 10 Feature Importance</h3>
              <div className="space-y-2">
                {Object.entries(result.training.feature_importance).map(([feature, importance]) => (
                  <div key={feature} className="flex items-center gap-3">
                    <span className="text-sm text-gray-600 w-40 truncate">{feature}</span>
                    <div className="flex-1 bg-gray-200 rounded-full h-4">
                      <div
                        className="bg-blue-500 h-4 rounded-full"
                        style={{ width: `${(importance as number) * 100}%` }}
                      ></div>
                    </div>
                    <span className="text-sm font-medium w-16 text-right">
                      {((importance as number) * 100).toFixed(1)}%
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Current Prediction */}
          <div className={`rounded-xl shadow p-6 ${result.current_prediction.direction === 'UP' ? 'bg-green-50' : 'bg-red-50'}`}>
            <h3 className="font-semibold text-gray-900 mb-4">Current Prediction for {result.symbol}</h3>
            <div className="flex items-center gap-6">
              <div className={`text-6xl ${result.current_prediction.direction === 'UP' ? 'text-green-600' : 'text-red-600'}`}>
                {result.current_prediction.direction === 'UP' ? '↑' : '↓'}
              </div>
              <div>
                <p className="text-2xl font-bold">Next Day: {result.current_prediction.direction}</p>
                <p className="text-gray-600">
                  Confidence: {(result.current_prediction.confidence * 100).toFixed(1)}%
                </p>
                {result.current_prediction.predicted_return_pct && (
                  <p className="text-gray-600">
                    Predicted Return: {result.current_prediction.predicted_return_pct.toFixed(3)}%
                  </p>
                )}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
